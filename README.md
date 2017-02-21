# p3_server
personal study for aiohttp based web server framework


安装虚拟环境软件 python3-env:

    apt-get install python3-venv


创建虚拟环境:

    python3 -m venv p3_project

激活虚拟环境:

    source p3_project/bin/active
    cd p3_project/

安装包:

    pip3 install aiohttp
    pip3 install aiohttp_debugtoolbar
    pip install aiomysql
    pip install aioredis
    pip install pyyaml
    pip3 install setproctitle
    
建立到本resp的软链接:
    
    ln -s ../p3_server/ api
    
建立配置文件夹和配置文件(使用自己的配置信息替换示例值):

    port: 8092
    debug: false
    proc_title: p3_api_server
    database:
        default:
            host: 1.2.3.4
            port: 3306
            user: xxx
            password: yyy
            db_name: zzz
        read:
            host: 1.2.3.4
            port: 3306
            user: xxx
            password: yyy
            db_name: zzz
        data:
            host: 1.2.3.4
            port: 3306
            user: xxx
            password: yyy
            db_name: zzz
        uc_read:
            host: 1.2.3.4
            port: 3307
            user: xxx
            password: yyy
            db_name: zzz
        db_score_common: &db_score
            host: 1.2.3.4
            port: 3307
            user: xxx
            password: yyy
        score_1:
            <<: *db_score
            db_name: db_score_0
        score_2:
            <<: *db_score
            db_name: db_score_1
        score_3:
            <<: *db_score
            db_name: db_score_3
        score_4:
            <<: *db_score
            db_name: db_score_4
        score_5:
            <<: *db_score
            db_name: db_score_5
        score_6:
            <<: *db_score
            db_name: db_score_6
        score_7:
            <<: *db_score
            db_name: db_score_7
        score_8:
            <<: *db_score
            db_name: db_score_8
        score_9:
            <<: *db_score
            db_name: db_score_9

    cache:
        default:
            host: 2.3.4.5
            port: 6379
            db: 1
            password: ""
        ad:
            host: 2.3.4.5
            port: 6380
            db: 1
            password: ""
        ad_slave:
            host: 2.3.4.5
            port: 6379
            db: 1
            password: ""

    user_service_list:
        server:
            - 2.3.4.5
        port:
            - 1234

    api_domain: b-api.aa123bb.com
    admin_domain: b-admin.aa123bb.com

    broker: redis://192.168.199.224:6379/1


    user_login_key: xyzxyz

   
启动服务:

    python server.py
    
