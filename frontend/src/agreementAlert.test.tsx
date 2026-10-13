import {render,screen,within} from '@testing-library/react';
import {it,expect} from 'vitest';
import {FrozenAlert} from './IndicatorAlerts';
import {supportedAgreementCapability,supportedAgreementBinding} from './agreementAlert';
import fixture from '../../tests/fixtures/agreement_ui_saved.json';
import {AGREEMENT_VERSION,AGREEMENT_WEIGHT_VERSION,AGREEMENT_MANIFEST_HASH} from './indicatorAgreement';
export const capability={version:1,predicate:'agreement',definition_version:2,contract:'frozen-indicator-alert-v2',agreement_version:AGREEMENT_VERSION,weight_version:AGREEMENT_WEIGHT_VERSION,manifest_hash:AGREEMENT_MANIFEST_HASH,directions:['up','down'],groups:['trend','momentum','volume'],threshold_min:0,threshold_max:1,threshold_inclusive:true,required_group_threshold:'strictly_greater_than_half'};
it('accepts the exact separately versioned agreement capability',()=>{expect(supportedAgreementCapability(capability)).toBe(true);expect(supportedAgreementBinding(fixture.definition.agreement)).toBe(true);});
it.each([
 ['version',2],['definition_version',3],['contract','future'],['agreement_version','future'],['weight_version','future'],['manifest_hash','wrong'],['directions',['up','down','neutral']],['groups',['trend','trend','volume']],['threshold_inclusive',false],['required_group_threshold','inclusive'],['threshold_max',100],['threshold_min',1],
])('rejects unsupported agreement capability %s without changing legacy catalog semantics',(key,value)=>{expect(supportedAgreementCapability({...capability,[key]:value})).toBe(false);});
it('rejects absent capability and duplicate binding members',()=>{expect(supportedAgreementCapability(undefined)).toBe(false);expect(supportedAgreementBinding({...fixture.definition.agreement,member_ids:['trend','trend']})).toBe(false);});
it('renders actual object-valued formula contracts and membership subset separately from numeric dependencies',()=>{
 const definition={...fixture.definition,instances:[...fixture.definition.instances,{id:'extra_numeric',type:'rsi',params:{period:14},contract:{display:'synthetic'}}]};
 render(<FrozenAlert definition={definition}/>);
 const region=screen.getByLabelText('Frozen agreement composition');
 expect(region.textContent).toContain('3 frozen agreement members');
 expect(region.textContent).toContain('Other frozen numeric/divergence dependencies (outside agreement membership): extra_numeric');
 expect(region.textContent).toContain('"period":2');expect(region.textContent).toContain('metadata_sha256');
 expect(screen.getByLabelText('Frozen alert definition').textContent).toContain('native interval 1m');
 expect(within(region).getAllByRole('listitem')).toHaveLength(4);
});
