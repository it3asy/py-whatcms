#!/usr/bin/env python
# coding: utf-8

import ConfigParser
import optparse
import requests
import urlparse
import pickle
import re,json,base64
import os, sys, inspect
from linkparser import *


reload(sys)
sys.setdefaultencoding('utf-8')

DEBUG_LEVEL = 1


ROOT_DIR=os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))


#In case you cannot install some of the required development packages, there's also an option to disable the SSL warning:
try:
	import requests.packages.urllib3
	requests.packages.urllib3.disable_warnings()
except:
    pass


def _debug(s,level):
	if level<=DEBUG_LEVEL:
		x = 32+level
		print '\033[0;%s;40m' % x + '  ' * (level-1) + '- %s' % s + '\033[0m'


def file_put_content(filename,content):
	return file(filename, 'wb').write(content)

def file_get_contents(filename):
	try:
	    with open(filename) as f:
	        return f.read()
	except Exception:
		return

def get_title(content):
	try:
		match = re.search('<title\s*?.*?>([\s\S]*?)</title>', content, re.IGNORECASE)
		if match:
			return match.group(1)
	except Exception:
		return
	return ''

def get_meta(content):
	return content

def get_charset(html, headers=[]):
	if html[0:3] == '\xef\xbb\xbf':
		return 'UTF-8'
	if dict(headers).has_key('Content-Type'):
		match = re.search('charset[\s]*?=[\s]*?[\'"]?([a-z0-9\-]+)[\'"]?', headers['Content-Type'], re.IGNORECASE)
		if match:
			codec = match.group(1).upper()
			if codec in ['UTF-8','GBK','GB2312','GB18030','BIG5']:
				return codec
			if codec.startswith('GB'):
				return 'GB18030'
	match = re.search('<meta\s[\s\S]*?charset[\s]*?=[\s]*?[\'"]?([a-z0-9\-]+)[\'"]?[\s\S]*?>', html, re.IGNORECASE)
	if match:
		codec = match.group(1).upper()
		if codec in ['UTF-8','GBK','GB2312','GB18030','BIG5']:
			return codec
		if codec.startswith('GB'):
			return 'GB18030'
	try_list = ["UTF-8", "GB18030", "BIG5"]
	for codec in try_list:
		try:
			decoded = html.decode(codec)
			return codec
		except:
			continue
	return 'UTF-8'

def get_baseurl(weburl):
	_urlObj = urlparse.urlparse(weburl)
	_basepath = _urlObj.path[0:_urlObj.path.rfind('/')]
	baseurl = '{0}://{1}/{2}'.format(_urlObj.scheme,_urlObj.netloc,_basepath)
	if not baseurl.endswith('/'):
		baseurl += '/'
	return baseurl


class FingerStuff(object):
	def __init__(self, finger):
		self.key = finger['key.words']
		self.key_func = finger['function']
		self.type = finger['type']
		self.rank = int(finger['rank'])
		self.url = finger['url']

		self.key_split = None
		if finger.has_key('key.split'):
			if len(finger['key.split']) > 0:
				self.key_split = finger['key.split']


		self.key_words = [self.key]
		if self.key_split:
			self.key_words = self.key.split(self.key_split)


		self.key_position = None
		if finger.has_key('key.position'):
			self.key_position = finger['key.position']


		self.key_logic = 'or'
		if finger.has_key('key.logic'):
			if finger['key.logic'].lower() == 'and':
				self.key_logic = 'and'

		self.key_ignorecase = 0
		if finger.has_key('ignorecase'):
			if finger['ignorecase'] == '1':
				self.key_ignorecase = 1

		self.flags = 0
		if finger.has_key('flags'):
			self.flags = int(finger['flags'])


class ContentStuff(object):
	def __init__(self, resp, exception):
		self.exception = None
		self.content = ''
		self.headers = []
		self.charset = 'GB18030'
		if not resp == None:
			self.headers = resp.headers
			self.charset = get_charset(html=resp.content, headers=self.headers)
			self.content = resp.content
			try:
				self.content = self.content.decode(self.charset, 'ignore')
			except:
				self.content = self.content.decode('GB18030', 'ignore')
			self.url = resp.url



class HttpStuff(object):
	def __init__(self, website):
		self.website = website
		self.cache_root = ROOT_DIR + '/' + 'cache/'
		self.cache_dir = self.cache_root + website.encode('hex') + '/'
		self.exception = None
		self.cache_cleanup()

		if not os.path.exists(self.cache_root):
			os.mkdir(self.cache_root)

	def __del__(self):
		self.cache_cleanup()

	def cache_cleanup(self):
		if os.path.exists(self.cache_dir):
			ld = os.listdir(self.cache_dir)
			for i in ld:
				f = self.cache_dir + '/' + i
				os.remove(f)
			os.rmdir(self.cache_dir)

	def cache_put(self, url, resp):
		if not os.path.exists(self.cache_dir):
			os.mkdir(self.cache_dir)
		filename = self.cache_dir + url.encode('hex')
		content =  pickle.dumps(resp)
		file_put_content(filename, content)

	def cache_get(self, url):
		filename = self.cache_dir + '/' + url.encode('hex')
		if os.path.exists(filename):
			content = file_get_contents(filename)
			resp = pickle.loads(content)
			return resp
		else:
			return None

	def get_content(self, url):
		resp = self.cache_get(url)
		if resp == None:
			headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language': 'en-GB,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate',
			'Connection': 'keep-alive'
			}
			session = requests.Session()
			try:
				resp = session.get(url, headers=headers, timeout=10, verify=False)
				self.exception = None
				self.cache_put(url, resp)
			except Exception as e:
				self.exception = str(e)
				resp = None
		
		return ContentStuff(resp, self.exception)



class WhatCMS(object):

	def __init__(self,target):
		self.config_suffix = 'conf'
		self.config_dir = ROOT_DIR + '/conf'
		self.website = target['website'].strip()
		self.baseurl = get_baseurl(self.website)
		self.specified = target['specified']
		self.platform = target['platform']

		self.cfg = ConfigParser.ConfigParser()

		self.httpstuff = HttpStuff(self.website)

		self.reqbad = [
			'connect timeout',
			'Connection timed out',
			'Read timed out',
			'No route to host',
			'Name or service not known',
			]


	def get_links(self, url):
		baseurl = get_baseurl(url)
		content = self.httpstuff.get_content(url).content
		links = LinksParser(baseurl,content).get_links_internal()
		return links


	def check_finger(self, finger):
		_type = finger.type
		_rank = finger.rank
		_url = finger.url
		_split = finger.key_split
		_logic = finger.key_logic
		_words = finger.key_words
		_func = finger.key_func
		_position = finger.key_position
		_ignorecase = finger.key_ignorecase

		_debug('_type=%s' % _type, 3)
		_debug('_url=%s' % _url, 3)
		_debug('_words=%s' % _words, 3)
		_debug('_position=%s' % _position, 3)
		_debug('_logic=%s' % _logic, 3)
		_debug('_func=%s' % _func, 3)

		if self.httpstuff.exception:
			for err in self.reqbad:
				if err in self.httpstuff.exception:
					_debug(self.httpstuff.exception, 2)
					return -1
		url = self.baseurl
		if _url.startswith('/'): 
			url=url.strip('/')
		url += _url
		stuff = self.httpstuff.get_content(url)
		if stuff.exception:
			_debug(self.httpstuff.exception, 2)
			for err in self.reqbad:
				if err in self.httpstuff.exception:
					_debug(self.httpstuff.exception, 2)
					return -1
			return -2

		content = stuff.content
		if content == '':
			if self.httpstuff.exception:
				_debug(self.httpstuff.exception, 2)
			return -2

		if _type == 'html':
			validate = False
			
			if _position == 'title':
				content = get_title(content)
				_debug('title is [%s]'%content, 2)
			elif _position == 'meta':
				content = get_meta(content)
			if content == None or content == '':
				return -3

			for keyword in _words:
				_debug('searching keyword [%s]'%keyword, 2)
				if _func == 're.search':
					flags = finger.flags
					match = re.search(keyword, content, flags)
					if match:
						validate = True
					else:
						validate = False
				elif _func == 'in':
					if _ignorecase == 1:
						keyword = keyword.lower()
						content = content.lower()
					if keyword in content:
						validate = True
					else:
						validate = False
				if _logic == 'and':
					if validate:
						_debug('validated go continue', 2)
						continue
					else:
						_debug('invalidated to break', 2)
						break
				elif _logic == 'or' and validate:
					if validate:
						_debug('validated go break', 2)
						break
					else:
						_debug('invalidated go continue', 2)
						continue

			if validate == True:
				_debug('return rank %s' % _rank, 2)
				return _rank
			else:
				_debug('return rank 0', 2)
				return 0

		if _type == 'url':
			validate = False
			links = self.get_links(url)

			if _position == 'urlparse.path':
				for i in range(len(links)):
					links[i] = urlparse.urlparse(links[i]).path
			elif _position == 'urlparse.query':
				for i in range(len(links)):
					links[i] = urlparse.urlparse(links[i]).query

			for keyword in _words:
				_debug('searching keyword [%s]'%keyword, 2)
				if _func == 're.search':
					flags = finger.flags
					for content in links:
						match = re.search(keyword, content, flags)
						if match:
							validate = True
							break
						else:
							validate = False
				elif _func == 'in':
					for content in links:
						if _ignorecase == 1:
							keyword = keyword.lower()
							content = content.lower()
						if keyword in content:
							validate = True
							break
						else:
							validate = False

				if _logic == 'and':
					if validate:
						_debug('validated go continue', 2)
						continue
					else:
						_debug('invalidated to break', 2)
						break
				elif _logic == 'or' and validate:
					if validate:
						_debug('validated go break', 2)
						break
					else:
						_debug('invalidated go continue', 2)
						continue

			if validate == True:
				_debug('return rank %s' % _rank, 2)
				return _rank
			else:
				_debug('return rank 0', 2)
				return 0

	def check_what(self):
		_debug(self.website, 1)
		if self.specified:		
			_debug('cms specified to %s'%self.specified, 1)
			ld = [self.specified + '.' + self.config_suffix]
		else:
			ld = os.listdir(self.config_dir)
		if self.platform:
			_debug('platform specified to %s'%self.platform, 1)
		for i in ld:
			conf = self.config_dir + '/' + i
			cfg = self.cfg#ConfigParser.ConfigParser()
			
			if not os.path.exists(conf):
				ld1 = os.listdir(self.config_dir)
				for j in ld1:
					conf1 = self.config_dir + '/' + j
					cfg.read(conf1)
					software = {}
					items= cfg.items('software')
					for item in items:
						software[item[0].lower()] = item[1].strip()
					if software['name'] == self.specified:
						conf = self.config_dir + '/' + j
						break

			if not os.path.exists(conf):
				_debug('error: cms %s not configed'%self.specified, 1)
			else:
				cfg.read(conf)
				software = {}
				items= cfg.items('software')
				for item in items:
					software[item[0].lower()] = item[1].strip()
				cmsname = software['name']
				if self.platform:
					platform = None
					if software.has_key('platform'):
						platform = software['platform']
					if not self.platform == platform:
						continue
				_debug('try cms %s' % cmsname,1)
				for section in cfg.sections():		
					if section.startswith('whatcms'):
						finger = {}
						items = cfg.items(section)
						for item in items:
							finger[item[0]] = item[1]
						_debug('checking finger %s'%section, 2)
						finger = FingerStuff(finger)
						ret = self.check_finger(finger)
						if ret == -1:
							_debug('error: bad request, exiting...', 1)
							return -1

						if ret == 1:
							return software

def whatcms(target,debug_level=0):
	global DEBUG_LEVEL
	DEBUG_LEVEL = debug_level
	cms = WhatCMS(target)
	what = cms.check_what()
	if what:
		return what


if __name__=='__main__':
	parser = optparse.OptionParser('usage: %prog [options] target.com')
	parser.add_option("-?", action="help", help=optparse.SUPPRESS_HELP)
	parser.add_option("-c", "--cms", dest="cms", action="append", help="specify cms name", metavar="cms")
	parser.add_option("-p", "--platform", dest="platform", action="append", help="specify platform", metavar="platform")
	parser.add_option("-d", "--debug", dest="debug", action="append", type=int,help="show debug log level", metavar="level")
	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.print_help()
		sys.exit(0)

	specified = None
	platform = None
	if options.cms:
		specified = options.cms[0]
	if options.debug:
		DEBUG_LEVEL = options.debug[0]
	if options.platform:
		platform = options.platform[0]

	target = {'website':args[0], 'specified':specified, 'platform':platform}

	r = whatcms(target,DEBUG_LEVEL)
	if r == -1:
		print 'Bad Networking'
	elif r:
		print 'Found [%s]' % r['name']
	else:
		print 'Not Found'

