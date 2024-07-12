# -*- coding: utf-8 -*-
# created by Venom for Fenomscrapers (2-10-2024)
'''
	Fenomscrapers Project
'''

from bs4 import BeautifulSoup as bs
import re
from openscrapers.modules import client
from openscrapers.modules import source_utils
from openscrapers.modules import control
from openscrapers.modules import log_utils
import bencodepy as bencode
import urllib.request as request
from urllib.parse import quote
import requests
import hashlib

class source:
	priority = 1
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['en']
		self.base_link = 'https://jackett.972437214.xyz'
		self.scraper_name = 'jackett'
		# self.movieSearch_link = '/providers=yts,eztv,rarbg,1337x,thepiratebay,kickasstorrents,torrentgalaxy|language=english/stream/movie/%s.json' # english is now default 12-09-2022
		# self.tvSearch_link = '/providers=yts,eztv,rarbg,1337x,thepiratebay,kickasstorrents,torrentgalaxy|language=english/stream/series/%s:%s:%s.json' # english is now default 12-09-2022
		# self.movieSearch_link = '/providers=yts,eztv,rarbg,1337x,thepiratebay,kickasstorrents,torrentgalaxy/stream/movie/%s.json'
		# self.tvSearch_link = '/providers=yts,eztv,rarbg,1337x,thepiratebay,kickasstorrents,torrentgalaxy/stream/series/%s:%s:%s.json'
		self.movieSearch_link = '/api/v2.0/indexers/all/results/torznab/?apikey=36uoqvh24k5gc0ljvk8y7hagngnkeql4&q=%s'
		self.tvSearch_link = '/api/v2.0/indexers/all/results/torznab/?apikey=36uoqvh24k5gc0ljvk8y7hagngnkeql4&q=%s'
		self.bypass_filter = control.setting('elfhosted.bypass_filter')
		self.min_seeders = 0

	def sources(self, data, hostDict):
		sources = []
		if not data: return sources
		if self.base_link == '':
			return sources
		sources_append = sources.append
		try:
			aliases = data['aliases']
			year = data['year']
			#imdb = data['imdb']
			if 'tvshowtitle' in data:
				title = data['tvshowtitle'].replace('&', 'and').replace('/', ' ').replace('$', 's')
				episode_title = data['title']
				season = data['season']
				episode = data['episode']
				hdlr = 'S%02dE%02d' % (int(season), int(episode))
				years = None
				url = '%s%s' % (self.base_link, self.tvSearch_link % quote(title))
			else:
				title = data['title'].replace('&', 'and').replace('/', ' ').replace('$', 's')
				episode_title = None
				hdlr = year
				years = [str(int(year)-1), str(year), str(int(year)+1)]
				url = '%s%s' % (self.base_link, self.movieSearch_link % quote(title))
			log_utils.log('url = %s' % url)
			results = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
			html = bs(results.text, 'html5lib')
			log_utils.log('results: '+results.text)
			log_utils.log('items: '+str(html('item')))
			try: files = html('item')
			except: return sources
			# _INFO = re.compile(r'👤.*')
			#_INFO = re.compile(r'💾.*')

			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error(self.scraper_name)
			return sources

		for item in files:
			try:
				#hash = file['infoHash']
				file_title = item.title.get_text(strip=True)
				log_utils.log('item: '+str(item))
				log_utils.log('item_title: '+file_title)
				#file_info = [x for x in file_title if _INFO.match(x)][0]
				name = source_utils.clean_name(file_title)
				log_utils.log('name: '+name)
				name_info = source_utils.info_from_name(name, title, year, hdlr, episode_title)
				log_utils.log('name_info: '+name_info)
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): 
					log_utils.log('error on undesirable')
					continue

				#url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name) 
				url =item.enclosure.get('url')
				torrent = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
				torrent_file = request.urlopen(torrent)
				metainfo = bencode.decode(torrent_file.read())
				info = bencode.encode(dict(metainfo.get(b'info')))
				hash = hashlib.sha1(info).hexdigest()
				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)
				log_utils.log('hash: '+hash)
				log_utils.log('url: '+url)
				try:
					seeders = int(item.find('torznab:attr', attrs={'name': 'seeders'})) 
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					torrent_size = item.find('torznab:attr', attrs={'name': 'size'})
					if torrent_size:
						torrent_size = torrent_size.get('value')
					if not torrent_size:
						torrent_size = item.size.get_text(strip=True)
					dsize, isize = source_utils.convert_size(float(torrent_size))
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				sources_append({'provider': self.scraper_name, 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info,
											'quality': quality, 'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize})
			except:
				source_utils.scraper_error(self.scraper_name)
		return sources

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		sources = []
		if not data: return sources
		sources_append = sources.append
		try:
			title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ').replace('$', 's')
			aliases = data['aliases']
			#imdb = data['imdb']
			year = data['year']
			season = data['season']
			url = '%s%s' % (self.base_link, self.tvSearch_link % quote(title))
			results = client.request(url, timeout=5)
			html = bs(results, 'html5lib')
			try: files = html('item')
			except: return sources
			# _INFO = re.compile(r'👤.*')
			#_INFO = re.compile(r'💾.*')
			undesirables = source_utils.get_undesirables()
			check_foreign_audio = source_utils.check_foreign_audio()
		except:
			source_utils.scraper_error(self.scraper_name)
			return sources

		for file in files:
			try:
				#hash = file['infoHash']
				file_title = item.title.get_text(strip=True)
				#file_info = [x for x in file_title if _INFO.match(x)][0]
				name = source_utils.clean_name(file_title[0])

				episode_start, episode_end = 0, 0
				if not search_series:
					if not bypass_filter:
						valid, episode_start, episode_end = source_utils.filter_season_pack(title, aliases, year, season, name.replace('.(Archie.Bunker', ''))
						if not valid: continue
					package = 'season'

				elif search_series:
					if not bypass_filter:
						valid, last_season = source_utils.filter_show_pack(title, aliases, imdb, year, season, name.replace('.(Archie.Bunker', ''), total_seasons)
						if not valid: continue
					else: last_season = total_seasons
					package = 'show'

				name_info = source_utils.info_from_name(name, title, year, season=season, pack=package)
				if undesirables and source_utils.remove_undesirables(name_info, undesirables): continue
				url =item.enclosure.get('url')
				torrent = request(url, headers={'User-Agent': 'Mozilla/5.0'})
				torrent_file = request.urlopen(torrent)
				metainfo = bencode.decode(torrent_file.read())
				info = bencode.encode(dict(metainfo.get(b'info')))
				hash = hashlib.sha1(info).hexdigest()
				url = 'magnet:?xt=urn:btih:%s&dn=%s' % (hash, name)
				try:
					seeders = int(item.find('torznab:attr', attrs={'name': 'seeders'}))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				quality, info = source_utils.get_release_quality(name_info, url)
				try:
					torrent_size = item.find('torznab:attr', attrs={'name': 'size'})
					if torrent_size:
						torrent_size = torrent_size.get('value')
					if not torrent_size:
						torrent_size = item.size.get_text(strip=True)
					dsize, isize = source_utils.convert_size(float(torrent_size))
					info.insert(0, isize)
				except: dsize = 0
				info = ' | '.join(info)

				item = {'provider': self.scraper_name, 'source': 'torrent', 'seeders': seeders, 'hash': hash, 'name': name, 'name_info': name_info, 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': dsize, 'package': package}
				if search_series: item.update({'last_season': last_season})
				elif episode_start: item.update({'episode_start': episode_start, 'episode_end': episode_end}) # for partial season packs
				sources_append(item)
			except:
				source_utils.scraper_error(self.scraper_name)
		return sources
