#-*- coding=utf-8 -*-

#限制调用域名
allow_site=['no-referrer'] #如果不限制，则添加：no-referrer

#######网站放数据的目录
config_dir='/root/pyone/data'

#######分享目录
share_path='/'

#######azure directory应用设置
client_id='' #Azure directory应用程序ID
client_secret='' #Azure directory密钥
redirect_uri='http://yourdomain' #你的域名，注册Azure directory时也填这个域名

#onedrive类型设置
od_type='business' #国际版：bussiness; 世纪互联版：bussiness_21v

#下载链接过期时间
downloadUrl_timeout=10*60 #默认10分钟过期

