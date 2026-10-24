from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
import sqlite3, os, hashlib, hmac, secrets, json, time, shutil

DB_PATH = os.getenv('PROJECTFORGE_DB', str(Path(__file__).parent / 'projectforge.db'))
UPLOAD_DIR = Path(os.getenv('PROJECTFORGE_UPLOAD_DIR', str(Path(__file__).parent / 'uploads'))).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SECRET = os.getenv('PROJECTFORGE_SECRET', 'change-this-secret-before-deployment').encode()
app = FastAPI(title='ProjectForge API', version='0.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','), allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 240000).hex()
    return f'{salt}${digest}'

def verify_password(password, stored):
    try:
        salt, digest = stored.split('$', 1)
        return hmac.compare_digest(hash_password(password, salt).split('$',1)[1], digest)
    except Exception: return False

def init_db():
    con = db()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member', active INTEGER NOT NULL DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '', owner_id INTEGER REFERENCES users(id), status TEXT DEFAULT 'Active', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS issues(id INTEGER PRIMARY KEY, issue_key TEXT UNIQUE NOT NULL, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, parent_id INTEGER REFERENCES issues(id) ON DELETE SET NULL, issue_type TEXT NOT NULL, summary TEXT NOT NULL, description TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'To Do', priority TEXT NOT NULL DEFAULT 'Medium', assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL, reporter_id INTEGER REFERENCES users(id), story_points REAL, due_date TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY, issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE, user_id INTEGER REFERENCES users(id), body TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, title TEXT NOT NULL, body TEXT DEFAULT '', author_id INTEGER REFERENCES users(id), updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sprints(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, name TEXT NOT NULL, goal TEXT DEFAULT '', state TEXT NOT NULL DEFAULT 'Planned', start_date TEXT, end_date TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sprint_issues(sprint_id INTEGER NOT NULL REFERENCES sprints(id) ON DELETE CASCADE, issue_id INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE, PRIMARY KEY(sprint_id, issue_id));
    CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY, issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE, document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE, filename TEXT NOT NULL, stored_name TEXT NOT NULL, content_type TEXT, size INTEGER NOT NULL, uploader_id INTEGER REFERENCES users(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP, CHECK ((issue_id IS NOT NULL) != (document_id IS NOT NULL))); 
    CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id INTEGER, details TEXT DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    if con.execute('SELECT COUNT(*) n FROM users').fetchone()['n'] == 0:
        con.execute('INSERT INTO users(username,full_name,email,password_hash,role) VALUES(?,?,?,?,?)', ('admin','ProjectForge Admin','admin@projectforge.local',hash_password('ChangeMe123!'),'admin'))
        uid = con.execute('SELECT id FROM users WHERE username=?',('admin',)).fetchone()['id']
        con.execute('INSERT INTO projects(key,name,description,owner_id) VALUES(?,?,?,?)',('DEMO','Demo Project','A sample project to explore ProjectForge.',uid))
        pid = con.execute('SELECT id FROM projects WHERE key=?',('DEMO',)).fetchone()['id']
        con.execute('INSERT INTO issues(issue_key,project_id,issue_type,summary,description,status,priority,assignee_id,reporter_id,story_points) VALUES(?,?,?,?,?,?,?,?,?,?)',('DEMO-1',pid,'Epic','Launch ProjectForge MVP','Deliver the first usable version of the project management tool.','In Progress','High',uid,uid,None))
        eid = con.execute('SELECT id FROM issues WHERE issue_key=?',('DEMO-1',)).fetchone()['id']
        con.execute('INSERT INTO issues(issue_key,project_id,parent_id,issue_type,summary,description,status,priority,assignee_id,reporter_id,story_points) VALUES(?,?,?,?,?,?,?,?,?,?,?)',('DEMO-2',pid,eid,'Story','Create project dashboard','Show project health and work distribution.','To Do','Medium',uid,uid,5))
        con.execute('INSERT INTO documents(project_id,title,body,author_id) VALUES(?,?,?,?)',(pid,'Project overview','## Objective\nBuild a lightweight, modular project management workspace.\n\n## Working agreements\n- Keep issues small and actionable.\n- Every issue should have an owner.\n- Track risks early.',uid))
    con.commit(); con.close()
init_db()

class LoginIn(BaseModel): username: str; password: str
class UserIn(BaseModel): username: str; full_name: str; email: str; password: str = Field(min_length=8); role: str = 'member'
class ProjectIn(BaseModel): key: str; name: str; description: str = ''; owner_id: Optional[int] = None
class IssueIn(BaseModel): project_id: int; issue_type: str; summary: str; description: str = ''; status: str = 'To Do'; priority: str = 'Medium'; parent_id: Optional[int] = None; assignee_id: Optional[int] = None; story_points: Optional[float] = None; due_date: Optional[str] = None
class IssuePatch(BaseModel): summary: Optional[str]=None; description: Optional[str]=None; status: Optional[str]=None; priority: Optional[str]=None; assignee_id: Optional[int]=None; parent_id: Optional[int]=None; story_points: Optional[float]=None; due_date: Optional[str]=None; issue_type: Optional[str]=None
class DocIn(BaseModel): project_id: int; title: str; body: str = ''
class CommentIn(BaseModel): body: str
class SprintIn(BaseModel): project_id: int; name: str; goal: str = ''; state: str = 'Planned'; start_date: Optional[str] = None; end_date: Optional[str] = None
class SprintPatch(BaseModel): name: Optional[str] = None; goal: Optional[str] = None; state: Optional[str] = None; start_date: Optional[str] = None; end_date: Optional[str] = None
class SprintIssueIn(BaseModel): issue_id: int

def token_for(user):
    payload = json.dumps({'uid': user['id'], 'exp': int(time.time())+86400}, separators=(',',':'))
    enc = __import__('base64').urlsafe_b64encode(payload.encode()).decode().rstrip('=')
    sig = hmac.new(SECRET, enc.encode(), hashlib.sha256).hexdigest()
    return enc+'.'+sig

def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Authentication required')
    try:
        enc,sig = authorization[7:].split('.',1)
        expected = hmac.new(SECRET,enc.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected): raise ValueError()
        payload = json.loads(__import__('base64').urlsafe_b64decode(enc+'='*(-len(enc)%4)))
        if payload['exp'] < time.time(): raise ValueError()
        con=db(); row=con.execute('SELECT id,username,full_name,email,role,active FROM users WHERE id=?',(payload['uid'],)).fetchone(); con.close()
        if not row or not row['active']: raise ValueError()
        return dict(row)
    except Exception: raise HTTPException(401,'Invalid or expired token')

def admin_user(user=Depends(current_user)):
    if user['role'] != 'admin': raise HTTPException(403,'Administrator role required')
    return user

def rowdict(row): return dict(row) if row else None
def audit(user, action, entity_type, entity_id, details=None):
    con=db(); con.execute('INSERT INTO audit_events(user_id,action,entity_type,entity_id,details) VALUES(?,?,?,?,?)',(user['id'],action,entity_type,entity_id,json.dumps(details or {}))); con.commit(); con.close()

@app.get('/api/health')
def health(): return {'status':'ok','app':'ProjectForge'}
@app.post('/api/auth/login')
def login(data: LoginIn):
    con=db(); user=con.execute('SELECT * FROM users WHERE username=? OR email=?',(data.username,data.username)).fetchone(); con.close()
    if not user or not user['active'] or not verify_password(data.password,user['password_hash']): raise HTTPException(401,'Invalid username or password')
    return {'access_token':token_for(user),'token_type':'bearer','user':{k:user[k] for k in ['id','username','full_name','email','role']}}
@app.get('/api/auth/me')
def me(user=Depends(current_user)): return user
@app.get('/api/users')
def users(user=Depends(current_user)):
    con=db(); rows=con.execute('SELECT id,username,full_name,email,role,active,created_at FROM users ORDER BY full_name').fetchall(); con.close(); return [dict(r) for r in rows]
@app.post('/api/users',status_code=201)
def create_user(data: UserIn, user=Depends(admin_user)):
    if data.role not in ('admin','manager','member','viewer'): raise HTTPException(400,'Invalid role')
    con=db()
    try:
        cur=con.execute('INSERT INTO users(username,full_name,email,password_hash,role) VALUES(?,?,?,?,?)',(data.username,data.full_name,data.email,hash_password(data.password),data.role)); con.commit(); uid=cur.lastrowid
        row=con.execute('SELECT id,username,full_name,email,role,active,created_at FROM users WHERE id=?',(uid,)).fetchone()
    except sqlite3.IntegrityError: con.close(); raise HTTPException(409,'Username or email already exists')
    con.close(); audit(user,'create','user',uid); return dict(row)
@app.get('/api/projects')
def projects(user=Depends(current_user)):
    con=db(); rows=con.execute('SELECT p.*,u.full_name owner_name,(SELECT COUNT(*) FROM issues i WHERE i.project_id=p.id) issue_count FROM projects p LEFT JOIN users u ON u.id=p.owner_id ORDER BY p.created_at DESC').fetchall(); con.close(); return [dict(r) for r in rows]
@app.post('/api/projects',status_code=201)
def create_project(data: ProjectIn,user=Depends(current_user)):
    key=data.key.upper().strip()
    if not key.replace('-','').isalnum(): raise HTTPException(400,'Project key must contain letters, numbers or hyphens')
    con=db()
    try:
        cur=con.execute('INSERT INTO projects(key,name,description,owner_id) VALUES(?,?,?,?)',(key,data.name,data.description,data.owner_id or user['id'])); con.commit(); pid=cur.lastrowid; row=con.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
    except sqlite3.IntegrityError: con.close(); raise HTTPException(409,'Project key already exists or owner is invalid')
    con.close(); audit(user,'create','project',pid); return dict(row)
@app.get('/api/issues')
def issues(project_id: Optional[int]=None, status: Optional[str]=None, issue_type: Optional[str]=None, user=Depends(current_user)):
    sql='SELECT i.*,p.key project_key,p.name project_name,u.full_name assignee_name,r.full_name reporter_name,parent.issue_key parent_key FROM issues i JOIN projects p ON p.id=i.project_id LEFT JOIN users u ON u.id=i.assignee_id LEFT JOIN users r ON r.id=i.reporter_id LEFT JOIN issues parent ON parent.id=i.parent_id WHERE 1=1'; args=[]
    if project_id: sql+=' AND i.project_id=?'; args.append(project_id)
    if status: sql+=' AND i.status=?'; args.append(status)
    if issue_type: sql+=' AND i.issue_type=?'; args.append(issue_type)
    sql+=' ORDER BY i.created_at DESC'
    con=db(); rows=con.execute(sql,args).fetchall(); con.close(); return [dict(r) for r in rows]
@app.post('/api/issues',status_code=201)
def create_issue(data: IssueIn,user=Depends(current_user)):
    allowed=('Epic','Story','Task','Bug','Sub-task','Spike')
    if data.issue_type not in allowed: raise HTTPException(400,'Unsupported issue type')
    if data.status not in ('To Do','In Progress','In Review','Done','Blocked'): raise HTTPException(400,'Invalid status')
    if data.priority not in ('Lowest','Low','Medium','High','Highest','Critical'): raise HTTPException(400,'Invalid priority')
    con=db(); p=con.execute('SELECT key FROM projects WHERE id=?',(data.project_id,)).fetchone()
    if not p: con.close(); raise HTTPException(404,'Project not found')
    seq=con.execute('SELECT COUNT(*) n FROM issues WHERE project_id=?',(data.project_id,)).fetchone()['n']+1; issue_key=f"{p['key']}-{seq}"
    try:
        cur=con.execute('INSERT INTO issues(issue_key,project_id,parent_id,issue_type,summary,description,status,priority,assignee_id,reporter_id,story_points,due_date) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(issue_key,data.project_id,data.parent_id,data.issue_type,data.summary,data.description,data.status,data.priority,data.assignee_id,user['id'],data.story_points,data.due_date)); con.commit(); iid=cur.lastrowid
        row=con.execute('SELECT * FROM issues WHERE id=?',(iid,)).fetchone()
    except sqlite3.IntegrityError: con.close(); raise HTTPException(400,'Invalid project, parent issue or assignee')
    con.close(); audit(user,'create','issue',iid,{'issue_key':issue_key}); return dict(row)
@app.patch('/api/issues/{issue_id}')
def update_issue(issue_id:int,data:IssuePatch,user=Depends(current_user)):
    changes=data.model_dump(exclude_unset=True)
    if not changes: raise HTTPException(400,'No changes supplied')
    allowed={'status':['To Do','In Progress','In Review','Done','Blocked'],'priority':['Lowest','Low','Medium','High','Highest','Critical'],'issue_type':['Epic','Story','Task','Bug','Sub-task','Spike']}
    for k,vals in allowed.items():
        if k in changes and changes[k] not in vals: raise HTTPException(400,f'Invalid {k}')
    changes['updated_at']='CURRENT_TIMESTAMP'
    sets=[]; args=[]
    for k,v in changes.items():
        if k=='updated_at': sets.append('updated_at=CURRENT_TIMESTAMP')
        else: sets.append(f'{k}=?'); args.append(v)
    args.append(issue_id); con=db(); cur=con.execute(f"UPDATE issues SET {', '.join(sets)} WHERE id=?",args); con.commit()
    if not cur.rowcount: con.close(); raise HTTPException(404,'Issue not found')
    row=con.execute('SELECT * FROM issues WHERE id=?',(issue_id,)).fetchone(); con.close(); audit(user,'update','issue',issue_id,changes); return dict(row)
@app.get('/api/issues/{issue_id}/comments')
def get_comments(issue_id:int,user=Depends(current_user)):
    con=db(); rows=con.execute('SELECT c.*,u.full_name username FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE issue_id=? ORDER BY c.created_at',(issue_id,)).fetchall(); con.close(); return [dict(r) for r in rows]
@app.post('/api/issues/{issue_id}/comments',status_code=201)
def add_comment(issue_id:int,data:CommentIn,user=Depends(current_user)):
    con=db()
    if not con.execute('SELECT id FROM issues WHERE id=?',(issue_id,)).fetchone(): con.close(); raise HTTPException(404,'Issue not found')
    cur=con.execute('INSERT INTO comments(issue_id,user_id,body) VALUES(?,?,?)',(issue_id,user['id'],data.body)); con.commit(); row=con.execute('SELECT * FROM comments WHERE id=?',(cur.lastrowid,)).fetchone(); con.close(); return dict(row)
@app.get('/api/documents')
def documents(project_id:Optional[int]=None,user=Depends(current_user)):
    con=db(); sql='SELECT d.*,p.key project_key,u.full_name author_name FROM documents d JOIN projects p ON p.id=d.project_id LEFT JOIN users u ON u.id=d.author_id'; args=[]
    if project_id: sql+=' WHERE d.project_id=?'; args.append(project_id)
    sql+=' ORDER BY d.updated_at DESC'; rows=con.execute(sql,args).fetchall(); con.close(); return [dict(r) for r in rows]
@app.post('/api/documents',status_code=201)
def create_document(data:DocIn,user=Depends(current_user)):
    con=db(); cur=con.execute('INSERT INTO documents(project_id,title,body,author_id) VALUES(?,?,?,?)',(data.project_id,data.title,data.body,user['id'])); con.commit(); row=con.execute('SELECT * FROM documents WHERE id=?',(cur.lastrowid,)).fetchone(); con.close(); return dict(row)
@app.get('/api/analytics/summary')
def summary(user=Depends(current_user)):
    con=db(); projects=con.execute('SELECT COUNT(*) n FROM projects').fetchone()['n']; total=con.execute('SELECT COUNT(*) n FROM issues').fetchone()['n'];
    statuses=[dict(r) for r in con.execute('SELECT status,COUNT(*) count FROM issues GROUP BY status')]; types=[dict(r) for r in con.execute('SELECT issue_type,COUNT(*) count FROM issues GROUP BY issue_type')]; priorities=[dict(r) for r in con.execute('SELECT priority,COUNT(*) count FROM issues GROUP BY priority')]; overdue=con.execute("SELECT COUNT(*) n FROM issues WHERE due_date < date('now') AND status!='Done'").fetchone()['n']; recent=[dict(r) for r in con.execute('SELECT i.issue_key,i.summary,i.status,i.priority,i.updated_at,p.key project_key FROM issues i JOIN projects p ON p.id=i.project_id ORDER BY i.updated_at DESC LIMIT 8')]; con.close()
    return {'project_count':projects,'issue_count':total,'overdue_count':overdue,'status_counts':statuses,'type_counts':types,'priority_counts':priorities,'recent_issues':recent}
@app.get('/api/audit')
def audit_log(limit:int=100,user=Depends(admin_user)):
    con=db(); rows=con.execute('SELECT a.*,u.username FROM audit_events a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT ?',(min(limit,500),)).fetchall(); con.close(); return [dict(r) for r in rows]


# ---- Editable resources, sprint planning, hierarchy and attachments ----
@app.patch('/api/projects/{project_id}')
def update_project(project_id: int, data: ProjectIn, user=Depends(current_user)):
    key=data.key.upper().strip()
    if not key or not key.replace('-','').isalnum(): raise HTTPException(400,'Invalid project key')
    con=db()
    try:
        cur=con.execute('UPDATE projects SET key=?,name=?,description=?,owner_id=? WHERE id=?',(key,data.name,data.description,data.owner_id,project_id)); con.commit()
        if not cur.rowcount: con.close(); raise HTTPException(404,'Project not found')
        row=con.execute('SELECT * FROM projects WHERE id=?',(project_id,)).fetchone()
    except sqlite3.IntegrityError: con.close(); raise HTTPException(409,'Project key already exists or owner is invalid')
    con.close(); audit(user,'update','project',project_id); return dict(row)

@app.delete('/api/projects/{project_id}', status_code=204)
def delete_project(project_id:int,user=Depends(current_user)):
    con=db(); cur=con.execute('DELETE FROM projects WHERE id=?',(project_id,)); con.commit(); con.close()
    if not cur.rowcount: raise HTTPException(404,'Project not found')
    audit(user,'delete','project',project_id); return None

@app.delete('/api/issues/{issue_id}', status_code=204)
def delete_issue(issue_id:int,user=Depends(current_user)):
    con=db(); cur=con.execute('DELETE FROM issues WHERE id=?',(issue_id,)); con.commit(); con.close()
    if not cur.rowcount: raise HTTPException(404,'Issue not found')
    audit(user,'delete','issue',issue_id); return None

@app.patch('/api/documents/{document_id}')
def update_document(document_id:int,data:DocIn,user=Depends(current_user)):
    con=db(); cur=con.execute('UPDATE documents SET project_id=?,title=?,body=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(data.project_id,data.title,data.body,document_id)); con.commit()
    if not cur.rowcount: con.close(); raise HTTPException(404,'Document not found')
    row=con.execute('SELECT * FROM documents WHERE id=?',(document_id,)).fetchone(); con.close(); audit(user,'update','document',document_id); return dict(row)

@app.delete('/api/documents/{document_id}',status_code=204)
def delete_document(document_id:int,user=Depends(current_user)):
    con=db(); cur=con.execute('DELETE FROM documents WHERE id=?',(document_id,)); con.commit(); con.close()
    if not cur.rowcount: raise HTTPException(404,'Document not found')
    audit(user,'delete','document',document_id); return None

@app.get('/api/sprints')
def list_sprints(project_id:Optional[int]=None,user=Depends(current_user)):
    con=db(); sql='SELECT s.*,p.key project_key,(SELECT COUNT(*) FROM sprint_issues si WHERE si.sprint_id=s.id) issue_count FROM sprints s JOIN projects p ON p.id=s.project_id'; args=[]
    if project_id: sql+=' WHERE s.project_id=?'; args.append(project_id)
    sql+=' ORDER BY s.created_at DESC'; rows=[dict(r) for r in con.execute(sql,args).fetchall()]
    for r in rows: r['issues']=[dict(x) for x in con.execute('SELECT i.id,i.issue_key,i.summary,i.status,i.issue_type,i.priority FROM sprint_issues si JOIN issues i ON i.id=si.issue_id WHERE si.sprint_id=? ORDER BY i.issue_key',(r['id'],)).fetchall()]
    con.close(); return rows

@app.post('/api/sprints',status_code=201)
def create_sprint(data:SprintIn,user=Depends(current_user)):
    if data.state not in ('Planned','Active','Completed'): raise HTTPException(400,'Invalid sprint state')
    con=db()
    if not con.execute('SELECT id FROM projects WHERE id=?',(data.project_id,)).fetchone(): con.close(); raise HTTPException(404,'Project not found')
    cur=con.execute('INSERT INTO sprints(project_id,name,goal,state,start_date,end_date) VALUES(?,?,?,?,?,?)',(data.project_id,data.name,data.goal,data.state,data.start_date,data.end_date)); con.commit(); row=con.execute('SELECT * FROM sprints WHERE id=?',(cur.lastrowid,)).fetchone(); con.close(); audit(user,'create','sprint',row['id']); return dict(row)

@app.patch('/api/sprints/{sprint_id}')
def update_sprint(sprint_id:int,data:SprintPatch,user=Depends(current_user)):
    changes=data.model_dump(exclude_unset=True)
    if 'state' in changes and changes['state'] not in ('Planned','Active','Completed'): raise HTTPException(400,'Invalid sprint state')
    if not changes: raise HTTPException(400,'No changes supplied')
    sets=[]; args=[]
    for k,v in changes.items(): sets.append(f'{k}=?'); args.append(v)
    sets.append('updated_at=CURRENT_TIMESTAMP'); args.append(sprint_id)
    con=db(); cur=con.execute(f"UPDATE sprints SET {','.join(sets)} WHERE id=?",args); con.commit()
    if not cur.rowcount: con.close(); raise HTTPException(404,'Sprint not found')
    row=con.execute('SELECT * FROM sprints WHERE id=?',(sprint_id,)).fetchone(); con.close(); audit(user,'update','sprint',sprint_id,changes); return dict(row)

@app.delete('/api/sprints/{sprint_id}',status_code=204)
def delete_sprint(sprint_id:int,user=Depends(current_user)):
    con=db(); cur=con.execute('DELETE FROM sprints WHERE id=?',(sprint_id,)); con.commit(); con.close()
    if not cur.rowcount: raise HTTPException(404,'Sprint not found')
    audit(user,'delete','sprint',sprint_id); return None

@app.post('/api/sprints/{sprint_id}/issues',status_code=201)
def add_sprint_issue(sprint_id:int,data:SprintIssueIn,user=Depends(current_user)):
    con=db(); sprint=con.execute('SELECT project_id FROM sprints WHERE id=?',(sprint_id,)).fetchone(); issue=con.execute('SELECT project_id FROM issues WHERE id=?',(data.issue_id,)).fetchone()
    if not sprint or not issue: con.close(); raise HTTPException(404,'Sprint or issue not found')
    if sprint['project_id'] != issue['project_id']: con.close(); raise HTTPException(400,'Issue and sprint must belong to the same project')
    con.execute('INSERT OR IGNORE INTO sprint_issues(sprint_id,issue_id) VALUES(?,?)',(sprint_id,data.issue_id)); con.commit(); con.close(); return {'ok':True}

@app.delete('/api/sprints/{sprint_id}/issues/{issue_id}',status_code=204)
def remove_sprint_issue(sprint_id:int,issue_id:int,user=Depends(current_user)):
    con=db(); con.execute('DELETE FROM sprint_issues WHERE sprint_id=? AND issue_id=?',(sprint_id,issue_id)); con.commit(); con.close(); return None

@app.get('/api/issues/{issue_id}/tree')
def issue_tree(issue_id:int,user=Depends(current_user)):
    con=db(); root=con.execute('SELECT * FROM issues WHERE id=?',(issue_id,)).fetchone()
    if not root: con.close(); raise HTTPException(404,'Issue not found')
    def node(row):
        item=dict(row); item['children']=[node(x) for x in con.execute('SELECT * FROM issues WHERE parent_id=? ORDER BY created_at',(row['id'],)).fetchall()]; return item
    result=node(root); con.close(); return result

@app.post('/api/issues/{issue_id}/attachments',status_code=201)
def upload_issue_attachment(issue_id:int,file:UploadFile=File(...),user=Depends(current_user)):
    con=db(); exists=con.execute('SELECT id FROM issues WHERE id=?',(issue_id,)).fetchone(); con.close()
    if not exists: raise HTTPException(404,'Issue not found')
    if not file.filename or len(file.filename)>255: raise HTTPException(400,'Invalid filename')
    stored=secrets.token_hex(16)+Path(file.filename).suffix[:16]; target=UPLOAD_DIR/stored
    size=0
    with target.open('wb') as out:
        while chunk:=file.file.read(1024*1024):
            size+=len(chunk)
            if size>25*1024*1024: out.close(); target.unlink(missing_ok=True); raise HTTPException(413,'Attachment exceeds 25 MB limit')
            out.write(chunk)
    con=db(); cur=con.execute('INSERT INTO attachments(issue_id,filename,stored_name,content_type,size,uploader_id) VALUES(?,?,?,?,?,?)',(issue_id,Path(file.filename).name,stored,file.content_type,size,user['id'])); con.commit(); row=con.execute('SELECT id,issue_id,filename,content_type,size,created_at FROM attachments WHERE id=?',(cur.lastrowid,)).fetchone(); con.close(); audit(user,'upload','attachment',cur.lastrowid); return dict(row)

@app.post('/api/documents/{document_id}/attachments',status_code=201)
def upload_document_attachment(document_id:int,file:UploadFile=File(...),user=Depends(current_user)):
    con=db(); exists=con.execute('SELECT id FROM documents WHERE id=?',(document_id,)).fetchone(); con.close()
    if not exists: raise HTTPException(404,'Document not found')
    if not file.filename or len(file.filename)>255: raise HTTPException(400,'Invalid filename')
    stored=secrets.token_hex(16)+Path(file.filename).suffix[:16]; target=UPLOAD_DIR/stored; size=0
    with target.open('wb') as out:
        while chunk:=file.file.read(1024*1024):
            size+=len(chunk)
            if size>25*1024*1024: target.unlink(missing_ok=True); raise HTTPException(413,'Attachment exceeds 25 MB limit')
            out.write(chunk)
    con=db(); cur=con.execute('INSERT INTO attachments(document_id,filename,stored_name,content_type,size,uploader_id) VALUES(?,?,?,?,?,?)',(document_id,Path(file.filename).name,stored,file.content_type,size,user['id'])); con.commit(); row=con.execute('SELECT id,document_id,filename,content_type,size,created_at FROM attachments WHERE id=?',(cur.lastrowid,)).fetchone(); con.close(); audit(user,'upload','attachment',cur.lastrowid); return dict(row)

@app.get('/api/issues/{issue_id}/attachments')
def issue_attachments(issue_id:int,user=Depends(current_user)):
    con=db(); rows=[dict(r) for r in con.execute('SELECT id,issue_id,filename,content_type,size,uploader_id,created_at FROM attachments WHERE issue_id=? ORDER BY created_at DESC',(issue_id,)).fetchall()]; con.close(); return rows

@app.get('/api/documents/{document_id}/attachments')
def document_attachments(document_id:int,user=Depends(current_user)):
    con=db(); rows=[dict(r) for r in con.execute('SELECT id,document_id,filename,content_type,size,uploader_id,created_at FROM attachments WHERE document_id=? ORDER BY created_at DESC',(document_id,)).fetchall()]; con.close(); return rows

@app.get('/api/attachments/{attachment_id}/download')
def download_attachment(attachment_id:int,user=Depends(current_user)):
    from fastapi.responses import FileResponse
    con=db(); row=con.execute('SELECT * FROM attachments WHERE id=?',(attachment_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404,'Attachment not found')
    path=UPLOAD_DIR/row['stored_name']
    if not path.exists(): raise HTTPException(404,'Attachment file missing')
    return FileResponse(path,filename=row['filename'],media_type=row['content_type'] or 'application/octet-stream')

@app.delete('/api/attachments/{attachment_id}',status_code=204)
def delete_attachment(attachment_id:int,user=Depends(current_user)):
    con=db(); row=con.execute('SELECT stored_name FROM attachments WHERE id=?',(attachment_id,)).fetchone()
    if not row: con.close(); raise HTTPException(404,'Attachment not found')
    (UPLOAD_DIR/row['stored_name']).unlink(missing_ok=True); con.execute('DELETE FROM attachments WHERE id=?',(attachment_id,)); con.commit(); con.close(); audit(user,'delete','attachment',attachment_id); return None
