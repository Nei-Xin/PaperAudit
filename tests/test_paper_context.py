from paperaudit.models import PaperChunk, ParsedPaper, PageRect
from paperaudit.paper_context import table_caption_links
from paperaudit.agents.code_tools import CodeWorkspace, MAX_RESULT_CHARS
from paperaudit.agents.code_investigator import CodeInvestigator, PaperQuote
from test_code_investigation import codebase, ScriptedClient, call, submit


def chunk(id, text, x=30, y=20, bottom=100, page=1, kind='text'):
    return PaperChunk(chunk_id=id,page=page,content=text,content_type=kind,
                      rects=[PageRect(x0=x,y0=y,x1=x+180,y1=bottom)])


def document(*chunks):
    return ParsedPaper(title='Tables',page_count=2,chunks=list(chunks))


def test_caption_link_requires_same_page_column_and_mutual_nearest_neighbor():
    body=chunk('body','config\nvalue\nwarmup epochs\n20')
    caption=chunk('caption','Table 2. Supervised training from scratch.',y=108,bottom=118)
    other_column=chunk('wrong-column','Table 1. Pre-training.',x=300,y=102,bottom=110)
    other_page=chunk('wrong-page','Table 3. Pre-training.',y=102,bottom=110,page=2)
    next_body=chunk('next','config\nvalue\nwarmup epochs\n40',y=130,bottom=200)
    next_caption=chunk('next-caption','Table 3. Pre-training.',y=208,bottom=218)
    links=table_caption_links(document(body,caption,other_column,other_page,next_body,next_caption))
    assert {k:v.chunk_id for k,v in links.items()}=={'body':'caption','next':'next-caption'}
    assert links['body'].text==caption.content


def test_ambiguous_missing_or_distant_layout_has_no_context():
    body=chunk('body','config\nvalue\nwarmup epochs\n20')
    above=chunk('a','Table 1. A.',y=2,bottom=12)
    below=chunk('b','Table 2. B.',y=108,bottom=118)
    assert not table_caption_links(document(body,above,below))
    assert not table_caption_links(document(body.model_copy(update={'rects':[]}),below))
    assert not table_caption_links(document(body,chunk('c','Table 3. C.',y=140,bottom=150)))
    assert not table_caption_links(document(chunk('p','We discuss results.'),below))
    assert not table_caption_links(document(chunk('empty','',kind='table'),below))


def test_tools_show_caption_and_only_then_persist_separate_context():
    body=chunk('body','config\nvalue\nwarmup epochs\n20')
    caption=chunk('caption','Table 2. Supervised training from scratch.',y=108,bottom=118)
    paper=document(body,caption)
    with CodeWorkspace(paper,codebase()) as workspace:
        text,_=workspace.run('grep_paper',{'text':'warmup'})
        assert caption.content in text and 'nearby_table_caption for=body' in text
        assert set(workspace.observed_chunks)=={'body','caption'}
        anchor=CodeInvestigator._paper_citation(PaperQuote(chunk_id='body',quote='warmup epochs 20'),workspace)
        assert anchor.text==body.content and anchor.source_context[0].chunk_id=='caption'
        assert anchor.source_context[0].page==1
        # Caption provenance is not permission to invent a concatenated quote.
        assert isinstance(CodeInvestigator._paper_citation(PaperQuote(chunk_id='body',
            quote='warmup epochs 20 Table 2. Supervised training from scratch.'),workspace),str)
    with CodeWorkspace(document(body.model_copy(update={'content':'x'*MAX_RESULT_CHARS,'content_type':'table'}),caption),codebase()) as workspace:
        assert not workspace._paper_blocks([workspace.paper_chunks['body']])
        assert not workspace.observed_chunks and not workspace.observed_context


def test_selected_table_is_shown_with_its_caption_without_reading_other_blocks():
    paper=document(chunk('body','config\nvalue\nwarmup epochs\n20'),
        chunk('caption','Table 2. Supervised training from scratch.',y=108,bottom=118),
        chunk('secret','UNRELATED_PRIVATE_BLOCK',x=300))
    client=ScriptedClient([submit(status='INSUFFICIENT_EVIDENCE',findings=[])])
    CodeInvestigator(client,paper,codebase(),'fake').run('warmup?','joint',selected_paper_chunk_ids=['body'])
    task=client.requests[0]['messages'][1]['content']
    assert 'Table 2. Supervised training from scratch.' in task
    assert 'UNRELATED_PRIVATE_BLOCK' not in task
