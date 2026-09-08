import pytest
from eval.luna_reliable_alignment import validate

def test_missing_facts_and_invented_claim_ids_are_rejected():
    facts=[{'fact_id':'F1'},{'fact_id':'F2'}];claims=[{'claim_id':'C1'}]
    with pytest.raises(AssertionError):
        validate({'matches':[{'fact_id':'F1','coverage':'full','claim_ids':['C1']}]},facts,claims)
    with pytest.raises(AssertionError):
        validate({'matches':[{'fact_id':'F1','coverage':'full','claim_ids':['C9']},
            {'fact_id':'F2','coverage':'missing','claim_ids':[]}]},facts,claims)
    validate({'matches':[{'fact_id':'F1','coverage':'full','claim_ids':['C1']},
        {'fact_id':'F2','coverage':'missing','claim_ids':[]}]},facts,claims)
