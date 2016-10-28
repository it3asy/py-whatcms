#coding: utf-8

import urlparse,re
from bs4 import BeautifulSoup

class LinksParser(object):
    """docstring for link_parser"""
    def __init__(self, baseurl, html_content):
        super(LinksParser, self).__init__()
        self.weburl = self.baseurl = baseurl

        # patch-001:
        # '''
        # html_content = '<html>xxx</html><script src="x"></script>'
        # BeautifulSoup cannot get script tag.
        # '''

        self.html_content = '<patch-001>'+html_content
        self.url_links = {
            'a':[],
            'link':[],
            'img':[],
            'script':[],
            'form':[],
            'location':[],
            'frame':[],
        }
        self.external_links = []
        self.internal_links = []
        self.soup = BeautifulSoup(self.html_content, 'lxml')
        self.get_baseurl()

    def get_baseurl(self):
        tag = self.soup.find('base')
        if tag and tag.attrs.has_key('href'):
            if not urlparse.urlparse(tag.attrs['href']).netloc == '':
                self.baseurl = tag.attrs['href']
        return self.baseurl

    def complet_url(self, link):
        if link.startswith('/') or link.startswith('.'):
            return urlparse.urljoin(self.baseurl, link)
        elif link.startswith('http') or link.startswith('https'):
            return link
        else:
            return urlparse.urljoin(self.baseurl, link)
            #return False

    def getall(self):
        self.get_tag_a()
        self.get_tag_link()
        self.get_tag_img()
        self.get_tag_script()
        self.get_tag_form()
        self.get_tag_location()
        self.get_tag_frame()
        # links 去重
        for child in self.url_links.keys():
            self.url_links[child] = list(set(self.url_links[child]))
        return self.url_links

    def get_tag_a(self):
        # 处理A链接
        for tag in self.soup.find_all('a'):
            if tag.attrs.has_key('href'):
                link = tag.attrs['href']
                # link = urlparse.urldefrag(tag.attrs['href'])[0] # 处理掉#tag标签信息
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['a'].append(complet_link)
        return self.url_links

    def get_tag_link(self):
        # 处理link链接资源
        for tag in self.soup.find_all('link'):
            if tag.attrs.has_key('href'):
                link = tag.attrs['href']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['link'].append(complet_link)
        return self.url_links

    def get_tag_img(self):
        for tag in self.soup.find_all('img'):
            if tag.attrs.has_key('src'):
                link = tag.attrs['src']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['img'].append(complet_link)
        return self.url_links

    def get_tag_script(self):
        for tag in self.soup.find_all('script'):
            if tag.attrs.has_key('src'):
                link = tag.attrs['src']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['script'].append(complet_link)
        return self.url_links

    def get_tag_location(self):
        for tag in self.soup.find_all('script'):
            text = tag.get_text()
            match = re.search('location(\.href)?\s*?=\s*?[\'"](.*?)[\'"]',text,re.IGNORECASE)
            if match:
                link = match.group(2)
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['location'].append(complet_link)
        return self.url_links
    
    def get_tag_form(self):
        for tag in self.soup.find_all('form'):
            if tag.attrs.has_key('action'):
                link = tag.attrs['action']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['form'].append(complet_link)
        return self.url_links

    def get_tag_frame(self):
        for tag in self.soup.find_all('frame'):
            if tag.attrs.has_key('src'):
                link = tag.attrs['src']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['frame'].append(complet_link)
        for tag in self.soup.find_all('iframe'):
            if tag.attrs.has_key('src'):
                link = tag.attrs['src']
                complet_link = self.complet_url(link.strip())
                if complet_link:
                    self.url_links['frame'].append(complet_link)
        return self.url_links['frame']

    def get_links_internal(self):
        b = self.getall()
        for a in b:
            for i in b[a]:
                p = urlparse.urlparse(i)
                if  p.netloc == urlparse.urlparse(self.weburl).netloc:
                    self.internal_links.append(i)
                else:
                    continue
        return self.internal_links

    def get_links_external(self):
        for i in self.getall()['a']:
            try:
                p = urlparse.urlparse(i)
                if  p.netloc == urlparse.urlparse(self.weburl).netloc:
                    continue
                else:
                    self.external_links.append(i)
            except Exception as e:
                print 'linkparser error:',i,'urlparse error'
        return self.external_links