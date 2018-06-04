#-*- coding=utf-8 -*-
from flask import Flask,render_template,redirect,abort,make_response,jsonify,request,url_for
from flask_sqlalchemy import Pagination
import json
from collections import OrderedDict
import subprocess
import hashlib
import random
from function import *
from config import *
from redis import Redis
import time
#######flask
app=Flask(__name__)
rd=Redis(host='localhost',port=6379)
################################################################################
###################################功能函数#####################################
################################################################################
def md5(string):
    a=hashlib.md5()
    a.update(string.encode(encoding='utf-8'))
    return a.hexdigest()

def FetchData(path='/',page=1,per_page=50):
    with open(os.path.join(config_dir,'data.json'),'r') as f:
        data=json.load(f, object_pairs_hook=OrderedDict)
    resp=[]
    if path=='/':
        items=data.items()
        total=len(items)
        for k,v in items[(page-1)*per_page:page*per_page]:
            item={}
            item['name']=k
            item['id']=v['id']
            item['lastModtime']=v['lastModtime']
            item['size']=v['size']
            item['type']=v['type'] if v['type']=='folder' else v['type'][0]
            item['downloadUrl']=v.get('downloadUrl')
            resp.append(item)
    else:
        route=path.split('/')
        cmd=u'data'
        for idx,r in enumerate(route):
            if idx==0:
                cmd+=u'.get(u"{}")'.format(r)
            else:
                cmd+=u'.get("value").get(u"{}")'.format(r)
            if idx==len(route)-1:
                cmd+=u'.get("value")'
        result=eval(cmd)
        items=result.items()
        total=len(items)
        for k,v in items[(page-1)*per_page:page*per_page]:
            item={}
            item['name']=k
            item['id']=v['id']
            item['lastModtime']=v['lastModtime']
            item['size']=v['size']
            item['type']=v['type'] if v['type']=='folder' else v['type'][0]
            item['downloadUrl']=v.get('downloadUrl')
            resp.append(item)
    return resp,total


def _getdownloadurl(id):
    app_url=GetAppUrl()
    token=GetToken()
    headers={'Authorization':'bearer {}'.format(token),'Content-Type':'application/json'}
    url=app_url+'_api/v2.0/me/drive/items/'+id
    r=requests.get(url,headers=headers)
    data=json.loads(r.content)
    if data.get('@content.downloadUrl'):
        return data.get('@content.downloadUrl')
    else:
        return True

def GetDownloadUrl(id):
    if rd.exists('downloadUrl:{}'.format(id)):
        downloadUrl,ftime=rd.get('downloadUrl:{}'.format(id)).split('####')
        if time.time()-int(ftime)>=600:
            print('{} downloadUrl expired!'.format(id))
            downloadUrl=_getdownloadurl(id)
            ftime=int(time.time())
            k='####'.join([downloadUrl,str(ftime)])
            rd.set('downloadUrl:{}'.format(id),k)
        else:
            print('get {}\'s downloadUrl from cache'.format(id))
            downloadUrl=downloadUrl
    else:
        print('first time get downloadUrl from {}'.format(id))
        downloadUrl=_getdownloadurl(id)
        ftime=int(time.time())
        k='####'.join([downloadUrl,str(ftime)])
        rd.set('downloadUrl:{}'.format(id),k)
    return downloadUrl


def GetName(id):
    with open(os.path.join(config_dir,'KeyValue.json'),'r') as f:
        kv=json.load(f)
    name=kv[id]['name']
    return name

def CodeType(ext):
    code_type={}
    code_type['html'] = 'html';
    code_type['htm'] = 'html';
    code_type['php'] = 'php';
    code_type['css'] = 'css';
    code_type['go'] = 'golang';
    code_type['java'] = 'java';
    code_type['js'] = 'javascript';
    code_type['json'] = 'json';
    code_type['txt'] = 'Text';
    code_type['sh'] = 'sh';
    code_type['md'] = 'Markdown';
    return code_type.get(ext.lower())

def file_ico(item):
  ext = item['name'].split('.')[-1].lower()
  if ext in ['bmp','jpg','jpeg','png','gif']:
    return "image";

  if ext in ['mp4','mkv','webm','avi','mpg', 'mpeg', 'rm', 'rmvb', 'mov', 'wmv', 'mkv', 'asf']:
    return "ondemand_video";

  if ext in ['ogg','mp3','wav']:
    return "audiotrack";

  return "insert_drive_file";

def _remote_content(item):
    fileid=item.get('id')
    downloadUrl=GetDownloadUrl(fileid)
    if downloadUrl:
        r=requests.get(downloadUrl)
        return r.content
    else:
        return False


def has_password(path):
    if not os.path.exists(os.path.join(config_dir,'data.json')):
        return False
    with open(os.path.join(config_dir,'data.json'),'r') as f:
        data=json.load(f, object_pairs_hook=OrderedDict)
    password=False
    if path=='/':
        if data.get('.password'):
            password=_remote_content(data.get('.password')).strip()
    else:
        route=path.split('/')
        cmd=u'data'
        for idx,r in enumerate(route):
            if idx==0:
                cmd+=u'.get(u"{}")'.format(unicode(r))
            else:
                cmd+=u'.get("value").get(u"{}")'.format(unicode(r))
            if idx==len(route)-1:
                cmd+=u'.get("value")'
        print cmd
        result=eval(cmd)
        if result.get('.password'):
            password=_remote_content(result.get('.password')).strip()
    return password


################################################################################
###################################试图函数#####################################
################################################################################
@app.before_request
def before_request():
    global referrer
    referrer=request.referrer if request.referrer is not None else 'no-referrer'


@app.route('/<path:path>',methods=['POST','GET'])
@app.route('/',methods=['POST','GET'])
def index(path='/'):
    code=request.args.get('code')
    page=request.args.get('page',1,type=int)
    password=has_password(path)
    print password
    md5_p=md5(path)
    if request.method=="POST":
        password1=request.form.get('password')
        print password1
        print password1==password
        if password1==password:
            resp=make_response(redirect(url_for('.index',path=path)))
            resp.delete_cookie(md5_p)
            resp.set_cookie(md5_p,password)
            return resp
    if password!=False:
        if not request.cookies.get(md5_p) or request.cookies.get(md5_p)!=password:
            return render_template('password.html',path=path)
    if code is not None:
        Atoken=OAuth(code)
        if Atoken.get('access_token'):
            with open(os.path.join(config_dir,'Atoken.json'),'w') as f:
                json.dump(Atoken,f,ensure_ascii=False)
            app_url=GetAppUrl()
            refresh_token=Atoken.get('refresh_token')
            with open(os.path.join(config_dir,'AppUrl'),w) as f:
                f.write(app_url)
            token=ReFreshToken(refresh_token)
            with open(os.path.join(config_dir,'token.json'),'w') as f:
                json.dump(token,f,ensure_ascii=False)
            return make_response('<h1>授权成功!<a href="/">点击进入首页</a></h1>')
        else:
            return jsonify(Atoken)
    else:
        if not os.path.exists(os.path.join(config_dir,'data.json')):
            if not os.path.exists(os.path.join(config_dir,'token.json')):
                return make_response('<h1><a href="{}">点击授权账号</a></h1>'.format(LoginUrl))
            else:
                subprocess.Popen('python function.py UpdateFile',shell=True)
                return make_response('<h1>正在更新数据!</h1>')
        items,total = FetchData(path,page)
        pagination=Pagination(query=None,page=page, per_page=50, total=total, items=None)
        return render_template('index.html',pagination=pagination,items=items,path=path,endpoint='.index')


@app.route('/file/<fileid>',methods=['GET','POST'])
def show(fileid):
    downloadUrl=GetDownloadUrl(fileid)
    if request.method=='POST':
        name=GetName(fileid)
        ext=name.split('.')[-1]
        url=request.url.replace(':80','').replace(':443','')
        if ext in ['csv','doc','docx','odp','ods','odt','pot','potm','potx','pps','ppsx','ppsxm','ppt','pptm','pptx','rtf','xls','xlsx']:
            url = 'https://view.officeapps.live.com/op/view.aspx?src='+urllib.quote(downloadUrl)
            return redirect(url)
        elif ext in ['bmp','jpg','jpeg','png','gif']:
            return render_template('show/image.html',downloadUrl=downloadUrl,url=url)
        elif ext in ['mp4','webm']:
            return render_template('show/video.html',downloadUrl=downloadUrl,url=url)
        elif ext in ['mp4','webm','avi','mpg', 'mpeg', 'rm', 'rmvb', 'mov', 'wmv', 'mkv', 'asf']:
            downloadUrl=downloadUrl.replace('thumbnail','videomanifest')+'&part=index&format=dash&useScf=True&pretranscode=0&transcodeahead=0'
            return render_template('show/video2.html',downloadUrl=downloadUrl,url=url)
        elif ext in ['ogg','mp3','wav']:
            return render_template('show/audio.html',downloadUrl=downloadUrl,url=url)
        elif CodeType(ext) is not None:
            content=requests.get(downloadUrl).content
            return render_template('show/code.html',content=content,url=url,language=CodeType(ext))
        else:
            content=requests.get(downloadUrl).content
            return render_template('show/any.html',content=content)
    else:
        if sum([i in referrer for i in allow_site])>0:
            return redirect(downloadUrl)
        else:
            return abort(404)



app.jinja_env.globals['FetchData']=FetchData
app.jinja_env.globals['file_ico']=file_ico
app.jinja_env.globals['title']='pyone'
################################################################################
#####################################启动#######################################
################################################################################
if __name__=='__main__':
    app.run(port=58693,debug=True)



