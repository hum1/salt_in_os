salt_in_os
==========
自建配置文件conf.py

默认.gitignore 被我忽视了

conf.py

DATABASES = {
    'default': {
         'ENGINE': 'django.db.backends.mysql',
         'NAME': 'mana',
         'USER': 'user',
         'PASSWORD': 'pwd',
         'HOST': 'your db host',
         'PORT': '',
    },
}
