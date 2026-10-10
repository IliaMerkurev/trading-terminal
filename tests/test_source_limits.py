import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from terminal import source_limits as limits
from terminal.data import DatasetStore, DataError, canonical
from terminal.series import Candle


class SourceLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=DatasetStore(Path(self.temp.name))
        bars=[Candle(i*60,100,101,99,100,10) for i in range(30)]
        self.manifest=self.store.save('linear','BTCUSDT',0,1800,bars,bars,{i*60:'0.001' for i in range(30)},
            metadata={'instrument':{'fundingInterval':1}},provenance=[])
        self.directory=self.store.root/self.manifest['id']

    def no_decode(self):
        return patch('pyarrow.parquet.ParquetFile.read',side_effect=AssertionError('Must reject before eager decode'))

    def replace_file(self,name,table,**kwargs):
        path=self.directory/(name+'.parquet');pq.write_table(table,path,**kwargs)
        self.manifest['files_sha256'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
        (self.directory/'manifest.json').write_bytes(canonical(self.manifest))

    def test_full_suffix_rejected_by_manifest_before_open_or_decode(self):
        # A tiny evaluation cannot authorize loading a larger full history.
        with patch.object(limits,'MAX_ROWS',29),self.no_decode(),patch('pyarrow.parquet.ParquetFile',side_effect=AssertionError('No footer needed')):
            with self.assertRaisesRegex(DataError,'Full source loading'):self.store.load(self.manifest['id'])

    def test_each_physical_table_count_is_checked_before_any_decode(self):
        for name in ('trade','mark','funding'):
            with self.subTest(name=name):
                table=pq.read_table(self.directory/(name+'.parquet'))
                self.replace_file(name,pa.concat_tables([table,table.slice(0,1)]))
                with patch.object(limits,'MAX_ROWS',30),self.no_decode():
                    with self.assertRaisesRegex(DataError,'Full source loading'):self.store.load(self.manifest['id'])
                self.replace_file(name,table)

    def test_metadata_file_footer_groups_and_decoded_estimate_limits(self):
        for key,value in [('MAX_MANIFEST_BYTES',10),('MAX_FILE_BYTES',10),('MAX_FOOTER_BYTES',10),
                          ('MAX_ROW_GROUPS',0),('MAX_ROW_GROUP_BYTES',1),('MAX_TOTAL_DECODED_BYTES',1),('MAX_MATERIALIZATION_BYTES',1)]:
            with self.subTest(key=key),patch.object(limits,key,value),self.no_decode():
                with self.assertRaisesRegex(DataError,'limit'):self.store.load(self.manifest['id'])

    def test_aggregate_all_tables_before_decode(self):
        sizes=[]
        for name in ('trade','mark','funding'):
            with (self.directory/(name+'.parquet')).open('rb') as stream:
                _,size=limits.checked_parquet(stream,name,self.manifest['files_sha256'][name]);sizes.append(size)
        self.assertGreater(sum(sizes),max(sizes))
        with patch.object(limits,'MAX_TOTAL_DECODED_BYTES',sum(sizes)-1),self.no_decode():
            with self.assertRaisesRegex(DataError,'Full source loading'):self.store.load(self.manifest['id'])
        with patch.object(limits,'MAX_TOTAL_DECODED_BYTES',sum(sizes)):
            self.assertEqual(len(self.store.load(self.manifest['id'])[1]),30)

    def test_bad_mark_and_funding_schemas_rejected_before_trade_decode(self):
        for name in ('mark','funding'):
            with self.subTest(name=name):
                original=pq.read_table(self.directory/(name+'.parquet'))
                self.replace_file(name,pa.table({'time':[0],'unexpected':['bad']}))
                with self.no_decode():
                    with self.assertRaisesRegex(DataError,'schema'):self.store.load(self.manifest['id'])
                self.replace_file(name,original)

    def test_large_funding_string_metadata_prevents_decode(self):
        original=pq.read_table(self.directory/'funding.parquet')
        self.replace_file('funding',pa.table({'time':pa.array([0],type=pa.int64()),'rate':['9'*8192]}))
        with patch.object(limits,'MAX_ROW_GROUP_BYTES',4096),self.no_decode():
            with self.assertRaisesRegex(DataError,'Full source loading'):self.store.load(self.manifest['id'])
        self.replace_file('funding',original)

    def test_checksums_and_normalized_hash_retained(self):
        path=self.directory/'mark.parquet';path.write_bytes(path.read_bytes()+b'bad')
        with self.no_decode():
            with self.assertRaisesRegex(DataError,'file checksum'):self.store.load(self.manifest['id'])

    def test_repeated_dictionary_string_expansion_rejected_before_decode(self):
        self.replace_file('funding',pa.table({'time':pa.array(range(30),type=pa.int64()),'rate':['9'*8192]*30}),use_dictionary=True)
        with patch.object(limits,'MAX_TOTAL_DECODED_BYTES',100000),self.no_decode():
            with self.assertRaisesRegex(DataError,'Full source loading'):self.store.load(self.manifest['id'])

    def test_manifest_declared_mark_and_funding_counts_rejected(self):
        for name in ('mark','funding'):
            changed={**self.manifest,'coverage':{**self.manifest['coverage'],name:{'count':2000001}}}
            with self.subTest(name=name),patch.object(self.store,'describe',return_value=changed),self.no_decode():
                with self.assertRaisesRegex(DataError,'Full source loading'):self.store.load(self.manifest['id'])

    def test_normalized_content_mismatch_still_rejected(self):
        table=pq.read_table(self.directory/'funding.parquet')
        self.replace_file('funding',table.set_column(1,'rate',pa.array(['0.002']*30)))
        with self.assertRaisesRegex(DataError,'Normalized dataset checksum'):self.store.load(self.manifest['id'])
