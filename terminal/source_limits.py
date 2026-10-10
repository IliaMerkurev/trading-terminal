"""Physical source admission shared by eager loading and bounded chart inspection.

Parquet byte estimates do not bound Python object overhead or process peak RAM.
"""
import hashlib
import json

import pyarrow.parquet as pq

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_FOOTER_BYTES = 4 * 1024 * 1024
MAX_ROWS = 2_000_000
MAX_ROW_GROUPS = 8192
MAX_ROW_GROUP_BYTES = 128 * 1024 * 1024
MAX_TOTAL_DECODED_BYTES = 512 * 1024 * 1024
MAX_MATERIALIZATION_BYTES = 1024 * 1024 * 1024
SOURCE_LIMIT = ('Full source loading exceeds limits (2,000,000 rows/table, 256 MiB/file, '
                '4 MiB/footer, 8,192 row groups, 128 MiB/row group, '
                '512 MiB total decoded-size estimate, 1 GiB materialization estimate). Prepare a smaller separate snapshot; '
                'evaluation dates do not reduce full source loading.')


def read_manifest(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError('Dataset manifest exceeds 4 MiB metadata limit')
    return json.loads(raw)


def check_manifest(manifest):
    step = manifest.get('interval_seconds', 60)
    bounds = manifest.get('range')
    if (type(step) is not int or step <= 0 or not isinstance(bounds, list) or len(bounds) != 2
            or any(type(v) is not int for v in bounds) or bounds[1] <= bounds[0]):
        raise ValueError('Invalid dataset source range')
    if (bounds[1] - bounds[0] + step - 1) // step > MAX_ROWS:
        raise ValueError(SOURCE_LIMIT)
    for name in ('trade', 'mark', 'funding'):
        coverage = manifest.get('coverage', {}).get(name)
        if coverage is None:continue
        count = coverage.get('count')
        if type(count) is not int or count < 0:raise ValueError('Invalid dataset source row count')
        if count > MAX_ROWS:raise ValueError(SOURCE_LIMIT)


def checked_parquet(stream, name, expected_hash, *, max_file_bytes=None, max_rows=None,
                    limit_message=SOURCE_LIMIT, checksum_message='Dataset file checksum mismatch'):
    """Check the same open descriptor later decoded; never eagerly read file bytes."""
    max_file_bytes = MAX_FILE_BYTES if max_file_bytes is None else max_file_bytes
    max_rows = MAX_ROWS if max_rows is None else max_rows
    stream.seek(0, 2); size = stream.tell()
    if size > max_file_bytes:raise ValueError(limit_message)
    stream.seek(0); sha = hashlib.sha256(); hashed = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        hashed += len(chunk)
        if hashed > max_file_bytes:raise ValueError(limit_message)
        sha.update(chunk)
    if sha.hexdigest() != expected_hash:raise ValueError(checksum_message)
    if size < 12:raise ValueError('Invalid local Parquet file')
    stream.seek(-8, 2); footer = stream.read(8)
    if footer[4:] != b'PAR1':raise ValueError('Invalid local Parquet footer')
    footer_size = int.from_bytes(footer[:4], 'little')
    if footer_size > MAX_FOOTER_BYTES:raise ValueError(limit_message)
    if footer_size > size - 12:raise ValueError('Invalid local Parquet footer length')
    stream.seek(0)
    parquet = pq.ParquetFile(stream, thrift_string_size_limit=1024*1024,
                             thrift_container_size_limit=100_000)
    metadata = parquet.metadata
    if not 0 <= metadata.num_rows <= max_rows or not 0 <= metadata.num_row_groups <= MAX_ROW_GROUPS:
        raise ValueError(limit_message)
    expected = {'time': 'int64', 'rate': 'string'} if name == 'funding' else {
        'time': 'int64', **{k: 'double' for k in ('open', 'high', 'low', 'close', 'volume')}}
    if len(parquet.schema_arrow) != len(expected) or {f.name: str(f.type) for f in parquet.schema_arrow} != expected:
        raise ValueError('Invalid local funding schema' if name == 'funding' else 'Invalid local candle schema')
    decoded_bytes = 0
    for i in range(metadata.num_row_groups):
        group = metadata.row_group(i)
        sizes=[group.total_byte_size]+[group.column(j).total_uncompressed_size for j in range(group.num_columns)]
        if group.num_rows < 0 or any(size < 0 for size in sizes):raise ValueError('Invalid Parquet size metadata')
        estimate = max(sizes[0],sum(sizes[1:]))
        if estimate > MAX_ROW_GROUP_BYTES:raise ValueError(limit_message)
        # Parquet uncompressed sizes still describe encoded pages. A string
        # dictionary can repeat one large value for every row. Bound that
        # expansion pessimistically before decode, rather than trusting rates.
        if name == 'funding':
            rate_index = parquet.schema_arrow.get_field_index('rate')
            estimate = max(estimate, group.num_rows * (group.column(rate_index).total_uncompressed_size + 12) + 4)
        decoded_bytes += estimate
        if decoded_bytes > MAX_TOTAL_DECODED_BYTES:raise ValueError(limit_message)
    return parquet, decoded_bytes


def policy():
    return dict(version=1,max_manifest_bytes=MAX_MANIFEST_BYTES,max_file_bytes=MAX_FILE_BYTES,
        max_footer_bytes=MAX_FOOTER_BYTES,max_rows_per_table=MAX_ROWS,max_row_groups=MAX_ROW_GROUPS,
        max_row_group_bytes=MAX_ROW_GROUP_BYTES,max_total_decoded_estimate_bytes=MAX_TOTAL_DECODED_BYTES,
        max_materialization_estimate_bytes=MAX_MATERIALIZATION_BYTES,
        candle_row_estimate_bytes=1024,funding_row_estimate_bytes=512,decoded_copy_factor=3,
        funding_string_estimate='row-group rows times uncompressed rate-column bytes',
        limitation='Admission estimates, not a process peak-RAM guarantee; all full source tables are loaded')


def check_materialization(checked, decoded_bytes):
    estimate = 3 * decoded_bytes + sum(parquet.metadata.num_rows * (512 if name == 'funding' else 1024)
                                     for name, parquet in checked.items())
    if estimate > MAX_MATERIALIZATION_BYTES:raise ValueError(SOURCE_LIMIT)
    return estimate
