"""Dependency-light browser demo for the enterprise support agent."""

from __future__ import annotations

import argparse
import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from enterprise_support_agent.agent.agent import EnterpriseSupportAgent
from enterprise_support_agent.config import Settings
from enterprise_support_agent.rag.knowledge_store import KnowledgeIngestionError, MultimodalKnowledgeStore


HTML = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>企业知识与客服 Agent</title><style>
:root{--ink:#152033;--muted:#637083;--line:#d8e0e8;--paper:#f5f7fa;--card:#fbfcfe;--nav:#111b2b;--accent:#23896f;--soft:#e4f2ed;--danger:#bd4d55}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 "Segoe UI","Microsoft YaHei",sans-serif}.shell{display:grid;grid-template-columns:230px 1fr;min-height:100vh}aside{background:var(--nav);color:#e7edf5;padding:28px 20px}.brand{font-size:20px;font-weight:750;letter-spacing:-.4px}.sub{color:#9eabba;font-size:12px;margin-top:6px}.nav{margin-top:32px;display:grid;gap:8px}.nav button{border:0;background:transparent;color:#b9c4d1;text-align:left;padding:12px;border-radius:8px;font-weight:650}.nav button.active{background:#203047;color:#fff}.mode{margin-top:28px;padding:12px;border:1px solid #314158;border-radius:10px;color:#b9c4d1;font-size:12px}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#58c99f;margin-right:7px}main{padding:30px 34px;max-width:1280px;width:100%}.top{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:22px}h1{font-size:26px;line-height:1.2;margin:0}.lead{color:var(--muted);margin:7px 0 0}.badge{padding:7px 10px;border-radius:7px;background:var(--soft);color:#17644f;font-weight:700;font-size:12px}.grid{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(320px,1fr);gap:18px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;box-shadow:0 8px 25px rgba(29,49,72,.06)}h2{font-size:15px;margin:0 0 14px}label{display:block;font-size:12px;font-weight:700;margin-bottom:7px}textarea{width:100%;min-height:112px;resize:vertical;border:1px solid #bec9d5;border-radius:8px;padding:12px;background:#fff;color:var(--ink);font:inherit;outline:none}textarea:focus,input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(35,137,111,.13)}button.primary{margin-top:12px;border:0;border-radius:8px;background:var(--accent);color:#fff;padding:11px 17px;font-weight:750;cursor:pointer}button:disabled{opacity:.55;cursor:wait}.answer{margin-top:16px;padding:14px;background:#f0f4f8;border-left:3px solid var(--accent);white-space:pre-wrap;min-height:58px}.meta{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin-top:10px}.sources{display:grid;gap:6px;margin-top:10px}.source{padding:8px 10px;border:1px solid var(--line);border-radius:7px;background:#fff;font-size:12px}.source b{color:#17644f}details{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}pre{overflow:auto;max-height:340px;background:#111b2b;color:#dce5ef;padding:13px;border-radius:8px;font:12px/1.55 Consolas,monospace}.drop{border:1px dashed #a8b6c5;border-radius:9px;padding:16px;text-align:center;background:#fff}.drop input{max-width:100%}.docs{display:grid;gap:9px;margin-top:14px}.doc{display:grid;grid-template-columns:1fr auto;gap:8px;padding:11px;border:1px solid var(--line);border-radius:8px}.doc small{display:block;color:var(--muted)}.delete{border:0;background:transparent;color:var(--danger);font-weight:700;cursor:pointer}.status{min-height:22px;color:var(--muted);font-size:12px;margin-top:9px}@media(max-width:860px){.shell{grid-template-columns:1fr}aside{padding:18px}.nav{display:none}main{padding:22px 16px}.grid{grid-template-columns:1fr}.top{align-items:start;flex-direction:column}}
</style></head><body><div class="shell"><aside><div class="brand">Support Lab</div><div class="sub">企业知识与客服 Agent</div><div class="nav"><span>任务控制台 · 知识管理 · 执行轨迹</span></div><div class="mode"><span class="dot"></span>本地演示模式<br>模拟订单与政策数据</div></aside><main><div class="top"><div><h1>企业知识与客服 Agent</h1><p class="lead">受控工具执行、来源可追踪的知识检索与人工升级。</p></div><span class="badge">Harness 已启用</span></div><div class="grid"><section class="card"><h2>运行客服任务</h2><label for="task">客户问题</label><textarea id="task">检查订单 ORD-1002，并解释适用的配送政策。</textarea><button class="primary" id="run">开始运行</button><div class="answer" id="answer">等待任务</div><div class="meta" id="meta"></div><div class="sources" id="sources"></div><details><summary>查看完整执行轨迹</summary><pre id="trace">{}</pre></details></section><section class="card"><h2>多模态知识管理</h2><div class="drop"><label for="file">添加 TXT、Markdown、PDF、PNG 或 JPEG</label><input id="file" type="file" accept=".txt,.md,.pdf,.png,.jpg,.jpeg"><button class="primary" id="upload">解析并建立索引</button></div><div class="status" id="uploadStatus"></div><div class="docs" id="docs"></div></section></div></main></div><script>
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const $=s=>document.querySelector(s);const fmt=n=>n<1024?n+' B':(n/1024).toFixed(1)+' KB';
async function json(url,options){const r=await fetch(url,options);const body=await r.json();if(!r.ok)throw new Error(body.error||'请求失败');return body}
async function loadDocs(){const body=await json('/api/documents');$('#docs').innerHTML=body.documents.length?body.documents.map(d=>`<div class="doc"><div><strong>${esc(d.filename)}</strong><small>${esc(d.status)} ${d.error?esc(d.error):esc(d.parser)} · ${d.chunk_count} 个分块 · ${fmt(d.size_bytes)}</small></div><button class="delete" data-id="${d.document_id}">删除</button></div>`).join(''):'<div class="status">尚未上传资料，内置政策库仍可检索。</div>';document.querySelectorAll('.delete').forEach(b=>b.onclick=async()=>{await json('/api/documents/'+b.dataset.id,{method:'DELETE'});loadDocs()})}
$('#run').onclick=async()=>{const b=$('#run');b.disabled=true;$('#answer').textContent='正在运行…';$('#sources').innerHTML='';try{const s=await json('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:$('#task').value})});$('#answer').textContent=s.final_answer;$('#meta').textContent=`停止原因 ${s.stop_reason} · ${s.turn_count} 轮 · ${s.latency_ms} ms`;$('#sources').innerHTML=s.sources.map(x=>`<div class="source"><b>来源</b> ${esc(x.source)}${x.page?' · 第 '+x.page+' 页':''}${x.score!==null&&x.score!==undefined?' · 相关度 '+x.score:''}</div>`).join('');$('#trace').textContent=JSON.stringify(s,null,2)}catch(e){$('#answer').textContent=e.message}finally{b.disabled=false}};
$('#upload').onclick=async()=>{const f=$('#file').files[0];if(!f){$('#uploadStatus').textContent='请先选择文件';return}const b=$('#upload');b.disabled=true;$('#uploadStatus').textContent='正在解析并建立索引…';try{const content=await new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result.split(',')[1]);r.onerror=no;r.readAsDataURL(f)});const d=await json('/api/documents',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:f.name,content_base64:content})});$('#uploadStatus').textContent=`已完成：${esc(d.filename)}，${d.chunk_count} 个分块`;loadDocs()}catch(e){$('#uploadStatus').textContent=e.message}finally{b.disabled=false}};loadDocs();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    settings = Settings()

    def _json(self, status: int, payload: object) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 12 * 1024 * 1024:
            raise ValueError("请求超过 12 MB 限制")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/":
            content = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        if urlparse(self.path).path == "/api/documents":
            store = MultimodalKnowledgeStore(self.settings.knowledge_uploads_path)
            self._json(200, {"documents": store.list_documents()})
            return
        self._json(404, {"error": "未找到接口"})

    def do_POST(self) -> None:
        try:
            body = self._body()
            path = urlparse(self.path).path
            if path == "/api/run":
                task = str(body.get("task", "")).strip()
                if not task:
                    raise ValueError("任务不能为空")
                self._json(200, EnterpriseSupportAgent(self.settings).run(task).to_dict())
                return
            if path == "/api/documents":
                filename = str(body.get("filename", ""))
                try:
                    content = base64.b64decode(body.get("content_base64", ""), validate=True)
                except Exception as error:
                    raise ValueError("文件内容不是有效 Base64") from error
                store = MultimodalKnowledgeStore(self.settings.knowledge_uploads_path)
                self._json(201, store.ingest(filename, content))
                return
            self._json(404, {"error": "未找到接口"})
        except (ValueError, KnowledgeIngestionError) as error:
            self._json(400, {"error": str(error)})
        except Exception as error:
            self._json(500, {"error": f"运行失败：{type(error).__name__}"})

    def do_DELETE(self) -> None:
        prefix = "/api/documents/"
        path = urlparse(self.path).path
        if not path.startswith(prefix):
            self._json(404, {"error": "未找到接口"})
            return
        document_id = unquote(path[len(prefix):])
        store = MultimodalKnowledgeStore(self.settings.knowledge_uploads_path)
        self._json(200 if store.delete(document_id) else 404, {"deleted": document_id})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Enterprise Support Agent web demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    print(f"Open http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
