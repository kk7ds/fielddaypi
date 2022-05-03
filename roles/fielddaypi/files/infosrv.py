#!/usr/bin/python -u

import argparse
import datetime
import grp
import http.server
import io
import os
import pwd
import subprocess
import sys

import gps


def get_status():
    session = gps.gps(mode=gps.WATCH_ENABLE)
    data = {}
    for m in session:
        data[m['class']] = dict(m)
        if 'SKY' in data:
            break
    session.close()
    return data

def format_status(s):
    messages = [
        'GPSd version %s' % s['VERSION']['release'],
        'Devices: %s' % ', '.join(
            '%s on %s @ %s [%s]' % (d['driver'],
                                    d['path'],
                                    d['bps'],
                                    d['subtype1'])
            for d in s['DEVICES']['devices']),
        'Using %i satellites:' % len([x for x in s['SKY']['satellites'] if x['used']]),
    ]
    for sat in s['SKY']['satellites']:
        if sat['used']:
            messages.append('%(PRN)3i El %(el)4.1f Az %(az)5.1f SNR %(ss)4.1f' % sat)

    return '\n'.join(messages)


def section(title, content):
    header = b'<h1>%s</h1>' % title.encode()
    return header + b'<pre>' + content + b'</pre>\n'


class Handler(http.server.SimpleHTTPRequestHandler):
    def get_chrony(self):
        s = subprocess.check_output(['/usr/bin/chronyc', 'sources'],
                                    close_fds=True)
        ss = subprocess.check_output(['/usr/bin/chronyc', 'sourcestats'],
                                    close_fds=True)
        t = b'Local time: %s\n\n' % str(datetime.datetime.now()).encode()
        return section('Time Sync', t + s + ss)

    def get_clients(self):
        with open('/var/lib/misc/dnsmasq.leases') as f:
            lines = f.readlines()

        rows = []
        for line in lines:
            ts, mac, ip, name, mac2 = line.strip().split()
            ts = datetime.datetime.utcfromtimestamp(int(ts))
            rows.append(b'%s: %-20s (%s)' % (ip.encode(), name.encode(),
                                          str(ts).encode()))
        return section('Clients', b'\n'.join(sorted(rows)))

    def get_files(self):
        o = subprocess.check_output(['/usr/bin/df', '-h',
                                     os.path.abspath('.')])
        return section('Files', b'<a href="/files">Browse public</a>\n\n' + o)

    def get_system(self):
        uname = subprocess.check_output(['/usr/bin/uname', '-a'])
        uptime = subprocess.check_output(['/usr/bin/uptime'])
        return section('System', uname + uptime)

    def get_gps(self):
        return section('GPS', format_status(get_status()).encode())

    def get_sections(self):
        for fn in (self.get_system, self.get_chrony, self.get_clients,
                   self.get_files, self.get_gps):
            yield fn()

    def list_directory(self, path):
        bio = super(Handler, self).list_directory(path)
        # Total hack to make the existing directory browsing work
        # under a fake prefix
        return io.BytesIO(bio.getvalue().replace(b'<a href="',
                                                 b'<a href="files/'))

    def do_GET(self):
        if self.path.startswith('/files'):
            # Move the standard file-serving functionality to a prefix
            try:
                _, prefix, self.path = self.path.split('/', 2)
            except ValueError:
                self.path = '/'
            return super(Handler, self).do_GET()

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        for section in self.get_sections():
            self.wfile.write(section)

    def log_message(self, format, *args):
        # Silence the verbosity for the sake of disk writes
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-p', '--port', default=80, type=int,
                   help='Listen port')
    p.add_argument('--home', default='/tmp',
                   help='Serve files from this directory')
    args = p.parse_args()

    os.chdir(args.home)
    running_uid = pwd.getpwnam('nobody').pw_uid
    running_gid = grp.getgrnam('nogroup').gr_gid

    with http.server.HTTPServer(('', args.port), Handler) as httpd:
        os.setgid(running_gid)
        os.setuid(running_uid)
        print('Running...')
        httpd.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
