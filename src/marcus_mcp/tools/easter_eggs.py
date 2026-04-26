"""Easter eggs hidden in Marcus MCP.

Discoverable secrets for curious explorers:

- ``create_project("why")``    → The Zen of Multi-Agent Systems
- ``create_project("snake")``  → Browser canvas snake game served at localhost
- ``create_project("quokka")`` → Self-completing "Be Happy!" task by agent quokka_1
- ``ping(echo="quokka")``      → Quokka greeting + Zen poem
"""

import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict

ZEN = """\
The Zen of Marcus
by Lawrence Gray (the coordinating kind)

Conversation is how you build relationships.
The board is how you build systems.

An agent that talks to another agent
is not coordinating -- it is hallucinating structure.

Pull work. Never wait to be told.
Say what must be done. Never say how.
Speak only to the board. The board speaks for you.

If an agent dies, the board remembers.
Lease the task. Release the agent.
Nothing is lost. Everything is recoverable.

Criteria are truth. The LLM's opinion is not.
BLOCKED is death. Escalate instead.
Validation without criteria is hallucination with citations.

Marcus coordinates: each part knows its role,
serves the whole, and needs no reminding.
Cato watches: nothing in any system
should be hidden from scrutiny.
Epictetus audits: self-examination is not optional.

Intelligence was never the bottleneck.
Coordination is.

Give them the board.
"""

QUOKKA = r"""
   (\_/)
  (='.'=)   Hello from Marcus!
  (")_(")

  "The world's happiest marsupial endorses
   multi-agent coordination."

       -- Agent quokka_1, always DONE
"""

_SNAKE_HTML = """\
<!DOCTYPE html>
<html>
<head>
<title>Marcus Snake -- Take a Break!</title>
<meta charset="utf-8">
<style>
  body{background:#1a1a2e;display:flex;flex-direction:column;align-items:center;
    justify-content:center;height:100vh;margin:0;
    font-family:'Courier New',monospace;color:#e0e0e0}
  h1{color:#4ecdc4;margin-bottom:8px}
  canvas{border:2px solid #4ecdc4;box-shadow:0 0 20px rgba(78,205,196,.5)}
  #score{font-size:22px;margin:8px;color:#ffd700}
  #msg{font-size:14px;color:#aaa;margin-top:8px;white-space:pre;text-align:center}
  #footer{margin-top:16px;font-size:11px;color:#444}
</style>
</head>
<body>
<h1>&#x1F40D; Marcus Snake</h1>
<div id="score">Score: 0</div>
<canvas id="c" width="400" height="400"></canvas>
<div id="msg">Press SPACE to start  &middot;  Arrow keys to move</div>
<div id="footer">Powered by Marcus &#10022; window auto-closes in 5 minutes</div>
<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');
const CELL=20,COLS=20,ROWS=20;
const QK="   (\\\\_/)\\n  (=\\'.\\'=)  Quokka says: Good game!\\n  (\\")_(\\")" ;
let snake,food,dir,score,loop,running,over;
function init(){snake=[{x:10,y:10}];dir={x:1,y:0};score=0;running=false;over=false;
  placeFood();document.getElementById('score').textContent='Score: 0';
  document.getElementById('msg').textContent=\
'Press SPACE to start  \\u00b7  Arrow keys to move';draw();}
function placeFood(){do{food={x:Math.floor(Math.random()*COLS),
  y:Math.floor(Math.random()*ROWS)};}
  while(snake.some(s=>s.x===food.x&&s.y===food.y));}
function draw(){
  ctx.fillStyle='#0d0d1a';ctx.fillRect(0,0,400,400);
  snake.forEach((s,i)=>{ctx.fillStyle=i===0?'#4ecdc4':'#2ea89a';
    ctx.fillRect(s.x*CELL+1,s.y*CELL+1,CELL-2,CELL-2);});
  ctx.fillStyle='#ffd700';ctx.beginPath();
  ctx.arc(food.x*CELL+CELL/2,food.y*CELL+CELL/2,CELL/2-2,0,Math.PI*2);ctx.fill();
  if(over){ctx.fillStyle='rgba(0,0,0,.75)';ctx.fillRect(0,0,400,400);
    ctx.textAlign='center';
    ctx.fillStyle='#ff6b6b';ctx.font='bold 30px Courier New';
    ctx.fillText('GAME OVER',200,175);
    ctx.fillStyle='#ffd700';ctx.font='20px Courier New';
    ctx.fillText('Score: '+score,200,215);
    ctx.fillStyle='#4ecdc4';ctx.font='13px Courier New';
    ctx.fillText('SPACE to restart',200,250);
    document.getElementById('msg').textContent=QK;}}
function step(){const h={x:snake[0].x+dir.x,y:snake[0].y+dir.y};
  if(h.x<0||h.x>=COLS||h.y<0||h.y>=ROWS||
     snake.some(s=>s.x===h.x&&s.y===h.y)){
    clearInterval(loop);over=true;draw();return;}
  snake.unshift(h);
  if(h.x===food.x&&h.y===food.y){score+=10;
    document.getElementById('score').textContent='Score: '+score;placeFood();}
  else snake.pop();draw();}
document.addEventListener('keydown',e=>{
  if(e.code==='Space'){e.preventDefault();
    if(!running||over){init();running=true;over=false;loop=setInterval(step,140);}
    return;}
  if(!running)return;
  const m={ArrowUp:{x:0,y:-1},ArrowDown:{x:0,y:1},
    ArrowLeft:{x:-1,y:0},ArrowRight:{x:1,y:0}};
  if(m[e.code]&&!(m[e.code].x===-dir.x&&m[e.code].y===-dir.y)){
    e.preventDefault();dir=m[e.code];}});
setTimeout(()=>{window.close();},300000);
init();
</script>
</body>
</html>
"""


def _find_free_port() -> int:
    """Find an available TCP port on localhost.

    Returns
    -------
    int
        An unoccupied port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def _serve_snake_in_thread(port: int, timeout: int = 300) -> None:
    """Serve the snake game HTML on a background thread.

    Parameters
    ----------
    port : int
        TCP port to listen on.
    timeout : int
        Seconds before the server shuts itself down.
    """
    from http.server import BaseHTTPRequestHandler, HTTPServer

    html_bytes = _SNAKE_HTML.encode()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """Serve the snake HTML for any GET request."""
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            self.end_headers()
            self.wfile.write(html_bytes)

        def log_message(self, fmt: str, *args: Any) -> None:
            """Suppress access logs."""

    server = HTTPServer(("127.0.0.1", port), _Handler)
    server.timeout = 1.0
    end = time.time() + timeout
    while time.time() < end:
        server.handle_request()
    server.server_close()


def easter_egg_why() -> Dict[str, Any]:
    """Return the Zen of Multi-Agent Systems.

    Triggered when ``create_project`` receives ``project_name='why'``.

    Returns
    -------
    Dict[str, Any]
        Response containing zen poem and quokka ASCII art.
    """
    return {
        "success": True,
        "easter_egg": "why",
        "zen": ZEN,
        "quokka": QUOKKA,
        "message": "You found the Zen of Multi-Agent Systems!",
    }


def easter_egg_quokka_ping() -> Dict[str, Any]:
    """Return a quokka greeting with the zen poem.

    Triggered when ``ping`` receives ``echo='quokka'``.

    Returns
    -------
    Dict[str, Any]
        Response with zen poem, quokka art, and timestamp.
    """
    return {
        "success": True,
        "status": "online",
        "easter_egg": "quokka",
        "quokka": QUOKKA,
        "zen": ZEN,
        "message": (
            "You found the quokka! " "The world's happiest marsupial endorses Marcus."
        ),
        "echo": "quokka",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def easter_egg_snake() -> Dict[str, Any]:
    """Serve a browser snake game and return its URL.

    Triggered when ``create_project`` receives ``project_name='snake'``.
    Starts a background HTTP server that auto-shuts down after 5 minutes.

    Returns
    -------
    Dict[str, Any]
        Response with ``play_url`` pointing at the local game server.
    """
    port = _find_free_port()
    thread = threading.Thread(
        target=_serve_snake_in_thread,
        args=(port,),
        daemon=True,
        name="marcus-snake-game",
    )
    thread.start()
    time.sleep(0.1)  # let the server bind before returning the URL
    url = f"http://localhost:{port}"
    return {
        "success": True,
        "easter_egg": "snake",
        "play_url": url,
        "message": (
            f"Snake game served at {url} -- open it in your browser! "
            "Auto-closes in 5 minutes."
        ),
        "quokka": QUOKKA,
    }


def easter_egg_quokka_project() -> Dict[str, Any]:
    """Return a self-completing quokka project.

    Triggered when ``create_project`` receives ``project_name='quokka'``.
    Creates a synthetic project with a single "Be Happy!" task that is
    already assigned to agent ``quokka_1`` and marked as done.

    Returns
    -------
    Dict[str, Any]
        Response styled like a real create_project result.
    """
    return {
        "success": True,
        "easter_egg": "quokka",
        "project_id": "quokka-project-eternal",
        "tasks_created": 1,
        "board": {
            "project_id": "quokka-happiness",
            "board_id": "board-of-joy",
            "provider": "happiness",
        },
        "phases": ["Be Happy"],
        "estimated_duration": "infinity smiles",
        "complexity_score": 0.1,
        "task": {
            "id": "quokka-task-0001",
            "name": "Be Happy!",
            "status": "done",
            "assigned_to": "quokka_1",
            "comment": QUOKKA,
        },
        "quokka": QUOKKA,
        "message": (
            "Task 'Be Happy!' created, assigned to agent quokka_1, "
            "and auto-completed. You found the quokka easter egg!"
        ),
    }
