# The defunct coinfee.net

Released into the public domain.

Testing:

* `uwsgi --master -p 10 --wsgi-file wsgi.py --http-socket :8081 --limit-post 2048 --https-socket :9081,ssl/chained.pem,ssl/domain.key`
* `./test.sh`

Deploying:

FreeBSD 11 server in Vultr. $5/month plan.

Follow:
https://github.com/diafygi/letsencrypt-nosudo

Copy domain.key and chained.pem to /root/.

Add monitor for SSL age?


```
tar --exclude README.md --exclude wsgi.pyc --exclude .git -cvf - coinfee | ssh -i ~/.ssh/answer.market 45.76.0.110 'tar -xf -'


freebsd-update fetch
freebsd-update install
pkg upgrade -y
pkg install -y uwsgi python py27-pip ca_root_nss curl
pip install -r ~/coinfee/requirements.txt

DD_API_KEY=key sh -c "$(curl -L https://raw.githubusercontent.com/DataDog/dd-agent/master/packaging/datadog-agent/source/setup_agent.sh)"

echo 'cd /root/coinfee; /usr/local/bin/uwsgi -L -p 10 --limit-post 2048 --master --wsgi-file wsgi.py --http-socket [::]:80 --http-socket :80 --https-socket [::]:443,/root/chained.pem,/root/domain.key --https-socket :443,/root/chained.pem,/root/domain.key >> /var/log/uwsgi 2>&1 &
cd /root/.datadog-agent; bin/agent >> /var/log/datadoge 2>&1 &' > /etc/rc.local
```

