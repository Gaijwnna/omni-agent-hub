import json,io,re,math,multiprocessing
from bs4 import BeautifulSoup
from pypdf import PdfReader

MAX_UPLOAD=5_000_000
MAX_OUTPUT=1_000_000

def convert_bytes(data:bytes,kind:str,output:str):
    if len(data)>MAX_UPLOAD:raise ValueError('Maximum upload size is 5 MB')
    if output not in ('json','markdown','llms'):raise ValueError('Unsupported output format')
    if kind=='pdf':
        if not data.startswith(b'%PDF-'):raise ValueError('Not a PDF file')
        reader=PdfReader(io.BytesIO(data))
        if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported')
        if len(reader.pages)>100:raise ValueError('Maximum PDF length is 100 pages')
        parts=[];total=0
        for page in reader.pages:
            part=page.extract_text() or '';total+=len(part)
            if total>MAX_OUTPUT:raise ValueError('Extracted text exceeds output limit')
            parts.append(part)
        content='\n\n'.join(parts)
        if not content.strip():raise ValueError('No extractable text. Scanned-image PDFs require OCR, which is not enabled.')
    else:
        content=data.decode('utf-8-sig')
        if kind=='html':
            soup=BeautifulSoup(content,'html.parser')
            for e in soup(['script','style','iframe','object','template']):e.decompose()
            content=soup.get_text('\n',strip=True)
        elif kind=='json':content=json.dumps(json.loads(content),ensure_ascii=False,indent=2)
        elif kind not in ('txt','markdown'):raise ValueError('Supported input types: PDF, TXT, HTML, JSON and Markdown')
    content='\n'.join(re.sub(r'[ \t]+',' ',line).strip() for line in content.splitlines()).strip()
    if len(content)>MAX_OUTPUT:raise ValueError('Extracted text exceeds output limit')
    result=json.dumps({'content':content},ensure_ascii=False,indent=2) if output=='json' else content
    # These are deliberately estimates, never branded as provider tokenizers.
    size=len(result.encode('utf-8'))
    estimate={'method':'UTF-8 byte heuristic; not a provider tokenizer','estimated_tokens':math.ceil(size/4),'range':[math.ceil(size/6),size],'applies_to':['OpenAI GPT-family','Anthropic Claude-family','Google Gemini-family'],'warning':'Actual counts vary with model, language and message framing; use the provider count endpoint for billing.'}
    return {'format':output,'content':result,'token_estimate':estimate,'uploads_retained':False,'retention':'Processed in memory in a bounded subprocess; no upload or extracted content is saved.'}

def child(pipe,data,kind,output):
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(15,15))
        pipe.send({'ok':convert_bytes(data,kind,output)})
    except Exception as e:pipe.send({'error':str(e)[:200]})
    finally:pipe.close()
def convert_isolated(data,kind,output):
    ctx=multiprocessing.get_context('spawn');parent,other=ctx.Pipe(duplex=False);proc=ctx.Process(target=child,args=(other,data,kind,output));proc.start();other.close()
    try:
        if not parent.poll(20):raise ValueError('Conversion exceeded the time limit')
        response=parent.recv()
        if 'error' in response:raise ValueError(response['error'])
        return response['ok']
    finally:
        if proc.is_alive():proc.terminate()
        proc.join(timeout=2);parent.close()
