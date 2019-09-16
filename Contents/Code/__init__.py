# XBMCnfoTVImporter
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
# Logo by CrazyRabbit
# Multi episode patch by random.server
# Fix of whole episodes getting cached as thumbnails by Em31Et
# Krypton ratings fix by F4RHaD
# Season banner and season art support by Christian
#
import os, re, time, datetime, platform, traceback, glob, re, htmlentitydefs
from dateutil.parser import parse
import urllib
import urlparse
import hashlib

PERCENT_RATINGS = {
  'rottentomatoes','rotten tomatoes','rt','flixster'
}

class xbmcnfotv(Agent.TV_Shows):
	name = 'XBMCnfoTVImporter'
	ver = '1.1-93-gc3e9112-220'
	primary_provider = True
	persist_stored_files = False
	languages = [Locale.Language.NoLanguage]
	accepts_from = ['com.plexapp.agents.localmedia','com.plexapp.agents.opensubtitles','com.plexapp.agents.podnapisi','com.plexapp.agents.plexthememusic','com.plexapp.agents.subzero']
	contributes_to = ['com.plexapp.agents.thetvdb']

##### helper functions #####
	def DLog (self, LogMessage):
		if Prefs['debug']:
			Log (LogMessage)

	def time_convert (self, duration):
		if (duration <= 2):
			duration = duration * 60 * 60 * 1000 #h to ms
		elif (duration <= 120):
			duration = duration * 60 * 1000 #m to ms
		elif (duration <= 7200):
			duration = duration * 1000 #s to ms
		return duration

	def checkFilePaths(self, pathfns, ftype):
		for pathfn in pathfns:
			if os.path.isdir(pathfn): continue
			self.DLog("Trying " + pathfn)
			if not os.path.exists(pathfn):
				continue
			else:
				Log("Found " + ftype + " file " + pathfn)
				return pathfn
		else:
			Log("No " + ftype + " file found! Aborting!")

	def RemoveEmptyTags(self, xmltags):
		for xmltag in xmltags.iter("*"):
			if len(xmltag):
				continue
			if not (xmltag.text and xmltag.text.strip()):
				#self.DLog("Removing empty XMLTag: " + xmltag.tag)
				xmltag.getparent().remove(xmltag)
		return xmltags

	##
	# Removes HTML or XML character references and entities from a text string.
	# Copyright: http://effbot.org/zone/re-sub.htm October 28, 2006 | Fredrik Lundh
	# @param text The HTML (or XML) source text.
	# @return The plain text, as a Unicode string, if necessary.

	def unescape(self, text):
		def fixup(m):
			text = m.group(0)
			if text[:2] == "&#":
				# character reference
				try:
					if text[:3] == "&#x":
						return unichr(int(text[3:-1], 16))
					else:
						return unichr(int(text[2:-1]))
				except ValueError:
					pass
			else:
				# named entity
				try:
					text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
				except KeyError:
					pass
			return text # leave as is
		return re.sub("&#?\w+;", fixup, text)

	##
	# Search and add to plex one or more posters, banners, arts, thumbnails or themes by show, season or episode.
	# author: https://github.com/joserick | J. Erick Carreon
	# email: support@joserick.com
	# date: Sep 12, 2019
	# @param metadata Objet Plex/MetadataModel
	# @param paths Paths where searches should be done.
	# @param type Type media (show|season|episode)
	# @param parts Parts of multi-episode.
	# @return void

	def AssetsLocal(self, metadata, paths, type, parts=[], multEpisode=False):
		pathFiles = {}
		audioExts = ['mp3', 'm4a']
		imageExts = ['jpg', 'png', 'jpeg', 'tbn']
		rootFile = os.path.splitext(os.path.basename(parts[0].file.encode("utf-8")))[0] if parts else None

		for path in paths:
			path = path.encode("utf-8")
			for filePath in sorted(os.listdir(path)):
				if filePath.endswith(tuple(imageExts + audioExts)):
					filePath = filePath.encode("utf-8")
					fullPath = os.path.join(path, filePath)
					if os.path.isfile(fullPath):
						pathFiles[filePath.lower()] = fullPath

		# Structure for Frodo, Eden and DLNA
		searchTuples = []
		if type == 'show':
			searchTuples.append(['(show|poster|folder)-?[0-9]?[0-9]?', metadata.posters, imageExts])
			searchTuples.append(['banner-?[0-9]?[0-9]?', metadata.banners, imageExts])
			searchTuples.append(['(fanart|art|background|backdrop)-?[0-9]?[0-9]?', metadata.art, imageExts])
			searchTuples.append(['theme-?[0-9]?[0-9]?', metadata.themes, audioExts])
		elif type == 'season':
			searchTuples.append(['season-?0?%s(-poster)?-?[0-9]?[0-9]?' % metadata.index, metadata.posters, imageExts])
			searchTuples.append(['season-?0?%s-banner-?[0-9]?[0-9]?' % metadata.index, metadata.banners, imageExts])
			searchTuples.append(['season-?0?%s-(fanart|art|background|backdrop)-?[0-9]?[0-9]?' % metadata.index, metadata.art, imageExts])
			if int(metadata.index) == 0:
				searchTuples.append(['season-specials-poster-?[0-9]?[0-9]?', metadata.posters, imageExts])
				searchTuples.append(['season-specials-banner-?[0-9]?[0-9]?', metadata.banners, imageExts])
				searchTuples.append(['season-specials-(fanart|art|background|backdrop)-?[0-9]?[0-9]?', metadata.art, imageExts])
		elif type == 'episode':
			searchTuples.append([re.escape(rootFile) + '(-|-thumb)?-?[0-9]?[0-9]?', metadata.thumbs, imageExts])

		for (structure, mediaList, exts) in searchTuples:
			validKeys = []
			sortIndex = 1
			filePathKeys = sorted(pathFiles.keys(), key = lambda x: os.path.splitext(x)[0])
			for filePath in filePathKeys:
				for ext in exts:
					if re.match('%s.%s' % (structure, ext), filePath, re.IGNORECASE):
						if multEpisode and ("-E" in filePath): continue

						data = Core.storage.load(pathFiles[filePath])
						mediaHash = filePath + hashlib.md5(data).hexdigest()

						validKeys.append(mediaHash)
						if mediaHash not in mediaList:
							mediaList[mediaHash] = Proxy.Media(data, sort_order = sortIndex)
							Log('Found season poster image at ' + filePath)
						else:
							Log('Skipping file %s file because it already exists.', filePath)
						sortIndex += 1

			Log('Found %d valid things for structure %s (ext: %s)', len(validKeys), structure, str(exts))
			validKeys = [value for value in mediaList.keys() if value in validKeys]
			mediaList.validate_keys(validKeys)

	def AssetsLink(self, nfoXML, metadata, type):
		validKeys = []
		searchTuples = [['poster', metadata.posters, 'thumb'], ['banner', metadata.banners, 'thumb'], ['art', metadata.art, 'fanart']]

		if type == 'show':
			searchTuples.append(['music', metadata.themes, 'theme'])

		Log('Search %s posters and banners from url', type)
		for mediaType, mediaList, tag in searchTuples:
			Log('Search %s %s form url', type, mediaType)
			try:
				if tag == 'fanart':
					nfoXMLAsset = nfoXML.xpath(tag)[0][0]
				else:
					nfoXMLAsset = nfoXML.xpath(tag)

					for asset in nfoXMLAsset:
						if asset.attrib.get('type', 'show') != type:
							continue
						if type == 'season' and metadata.index != int(asset.attrib.get('season')):
							continue
						if tag != 'thumb' or str(asset.attrib.get('aspect')) == mediaType:
							Log('Trying to get ' + mediaType)
							try:
								mediaList[asset.text] = Proxy.Media(HTTP.Request(asset.getparent().attrib.get('url', '') + asset.text))
								validKeys.append(asset.text)
								Log('Found %s %s at %s', type, mediaType, asset.text)
							except Exception, e:
								Log('Error getting %s at %s: %s', mediaType, asset.text, str(e))

					mediaList.validate_keys(list(set(validKeys) & set(mediaList.keys())))
			except Exception, e:
				Log('Error getting %s %s: %s', type, mediaType, str(e))

##### search function #####
	def search(self, results, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering search function")
		self.DLog("++++++++++++++++++++++++")
		Log ("" + self.name + " Version: " + self.ver)
		self.DLog("Plex Server Version: " + Platform.ServerVersion)

		if Prefs['debug']:
			Log ('Agents debug logging is enabled!')
		else:
			Log ('Agents debug logging is disabled!')

		id = media.id
		path1 = None
		try:
			pageUrl = "http://127.0.0.1:32400/library/metadata/" + id + "/tree"
			nfoXML = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
			filename = os.path.basename(String.Unquote(nfoXML.get('file').encode('utf-8')))
			path1 = os.path.dirname(String.Unquote(nfoXML.get('file').encode('utf-8')))
		except:
			self.DLog ('Exception nfoXML.get(''file'')!')
			self.DLog ("Traceback: " + traceback.format_exc())
			pass
			return

		self.DLog("Path from XML: " + str(path1))
		path = os.path.dirname(path1)
		nfoName = os.path.join(path, "tvshow.nfo")
		self.DLog('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			nfoName = os.path.join(path1, "tvshow.nfo")
			self.DLog('Looking for TV Show NFO file at ' + nfoName)
			path = path1
		if not os.path.exists(nfoName):
			path2 = os.path.dirname(os.path.dirname(path))
			nfoName = os.path.join(path2, "tvshow.nfo")
			self.DLog('Looking for TV Show NFO file at ' + nfoName)
			path = path2
		if not os.path.exists(nfoName):
			path = os.path.dirname(path1)

		year = 0
		if media.title:
			title = media.title
		else:
			title = "Unknown"


		if not os.path.exists(nfoName):
			self.DLog("Couldn't find a tvshow.nfo file; will try to guess from filename...:")
			regtv = re.compile('(.+?)'
				'[ .]S(\d\d?)E(\d\d?)'
				'.*?'
				'(?:[ .](\d{3}\d?p)|\Z)?')
			tv = regtv.match(filename)
			if tv:
				title = tv.group(1).replace(".", " ")
			self.DLog("Using tvshow.title = " + title)
		else:
			nfoFile = nfoName
			Log("Found nfo file at " + nfoFile)
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			# remove empty xml tags from nfo
			self.DLog('Removing empty XML tags from tvshows nfo...')
			nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags = re.MULTILINE)

			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</tvshow>' % nfoText.split('</tvshow>')[0]

				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return
				Log(nfoXML.xpath("title"))

				# Title
				try: title = nfoXML.xpath("title")[0].text
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Sort Title
				try: media.title_sort = nfoXML.xpath("sorttitle")[0].text
				except:
					self.DLog("No <sorttitle> tag in " + nfoFile + ".")
					pass
				# ID
				try: id = nfoXML.xpath("id")[0].text
				except:
					id = None

		# if tv show id doesn't exist, create
		# one based on hash of title
		if not id:
			ord3 = lambda x : '%.3d' % ord(x)
			id = int(''.join(map(ord3, title)))
			id = str(abs(hash(int(id))))

			Log('ID: ' + str(id))
			Log('Title: ' + str(title))
			Log('Year: ' + str(year))

		results.Append(MetadataSearchResult(id=id, name=title, year=year, lang=lang, score=100))
		Log('scraped results: ' + str(title) + ' | year = ' + str(year) + ' | id = ' + str(id))

##### update Function #####
	def update(self, metadata, media, lang):
		self.DLog("++++++++++++++++++++++++")
		self.DLog("Entering update function")
		self.DLog("++++++++++++++++++++++++")
		Log ("" + self.name + " Version: " + self.ver)
		self.DLog("Plex Server Version: " + Platform.ServerVersion)

		if Prefs['debug']:
			Log ('Agents debug logging is enabled!')
		else:
			Log ('Agents debug logging is disabled!')

		Dict.Reset()
		metadata.duration = None
		id = media.id
		duration_key = 'duration_'+id
		Dict[duration_key] = [0] * 200
		Log('Update called for TV Show with id = ' + id)
		path1 = None
		try:
			pageUrl = "http://127.0.0.1:32400/library/metadata/" + id + "/tree"
			nfoXML = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
			filename = os.path.basename(String.Unquote(nfoXML.get('file').encode('utf-8')))
			path1 = os.path.dirname(String.Unquote(nfoXML.get('file').encode('utf-8')))
		except:
			self.DLog ('Exception nfoXML.get(''file'')!')
			self.DLog ("Traceback: " + traceback.format_exc())
			pass
			return


		self.DLog("Path from XML: " + str(path1))
		path = os.path.dirname(path1)
		nfoName = os.path.join(path, "tvshow.nfo")
		self.DLog('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			nfoName = os.path.join(path1, "tvshow.nfo")
			self.DLog('Looking for TV Show NFO file at ' + nfoName)
			path = path1
		if not os.path.exists(nfoName):
			path2 = os.path.dirname(os.path.dirname(path))
			nfoName = os.path.join(path2, "tvshow.nfo")
			self.DLog('Looking for TV Show NFO file at ' + nfoName)
			path = path2
		if not os.path.exists(nfoName):
			path = os.path.dirname(path1)

		if media.title:
			title = media.title
		else:
			title = "Unknown"

		if not os.path.exists(nfoName):
			self.DLog("Couldn't find a tvshow.nfo file; will try to guess from filename...:")
			regtv = re.compile('(.+?)'
				'[ .]S(\d\d?)E(\d\d?)'
				'.*?'
				'(?:[ .](\d{3}\d?p)|\Z)?')
			tv = regtv.match(filename)
			if tv:
				title = tv.group(1).replace(".", " ")
				metadata.title = title
			Log("Using tvshow.title = " + title)
		else:
			nfoFile = nfoName
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
			# remove empty xml tags from nfo
			self.DLog('Removing empty XML tags from tvshows nfo...')
			nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags = re.MULTILINE)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</tvshow>' % nfoText.split('</tvshow>')[0]

				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					self.DLog('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				#remove remaining empty xml tags
				self.DLog('Removing remaining empty XML tags from tvshows nfo...')
				nfoXML = self.RemoveEmptyTags(nfoXML)

				# Title
				try: metadata.title = nfoXML.xpath("title")[0].text
				except:
					self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Sort Title
				try: metadata.title_sort = nfoXML.xpath("sorttitle")[0].text
				except:
					self.DLog("No <sorttitle> tag in " + nfoFile + ".")
					pass
				# Original Title
				try: metadata.original_title = nfoXML.xpath('originaltitle')[0].text
				except: pass
				# Content Rating
				try:
					mpaa = nfoXML.xpath('./mpaa')[0].text
					match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
					if match.group('mpaa'):
						content_rating = match.group('mpaa')
					else:
						content_rating = 'NR'
					metadata.content_rating = content_rating
				except: pass
				# Network
				try: metadata.studio = nfoXML.xpath("studio")[0].text
				except: pass
				# Premiere
				try:
					air_string = None
					try:
						self.DLog("Reading aired tag...")
						air_string = nfoXML.xpath("aired")[0].text
						self.DLog("Aired tag is: " + air_string)
					except:
						self.DLog("No aired tag found...")
						pass
					if not air_string:
						try:
							self.DLog("Reading premiered tag...")
							air_string = nfoXML.xpath("premiered")[0].text
							self.DLog("Premiered tag is: " + air_string)
						except:
							self.DLog("No premiered tag found...")
							pass
					if not air_string:
						try:
							self.DLog("Reading dateadded tag...")
							air_string = nfoXML.xpath("dateadded")[0].text
							self.DLog("Dateadded tag is: " + air_string)
						except:
							self.DLog("No dateadded tag found...")
							pass
					if air_string:
						try:
							if Prefs['dayfirst']:
								dt = parse(air_string, dayfirst=True)
							else:
								dt = parse(air_string)
							metadata.originally_available_at = dt
							self.DLog("Set premiere to: " + dt.strftime('%Y-%m-%d'))
						except:
							self.DLog("Couldn't parse premiere: " + traceback.format_exc())
							pass
				except:
					self.DLog("Exception parsing Premiere: " + traceback.format_exc())
					pass
				metadata.summary = ''
				# Status
				try:
					status = nfoXML.xpath('status')[0].text.strip()
					if Prefs['statusinsummary']:
						self.DLog('User setting adds show status (' + status + ') in front of summary...')
						metadata.summary = 'Status: ' + status + ' | '
				except:
					pass
				# Tagline - not supported by TVShow Object!!!
				try: metadata.tagline = nfoXML.findall("tagline")[0].text
				except: pass
				# Summary (Plot)
				try: metadata.summary = metadata.summary + nfoXML.xpath("plot")[0].text
				except:
					pass
				# Ratings
				try:
					nforating = round(float(nfoXML.xpath("rating")[0].text.replace(',', '.')),1)
					metadata.rating = nforating
					self.DLog("Series Rating found: " + str(nforating))
				except:
					self.DLog("Can't read rating from tvshow.nfo.")
					self.DLog("Trying to get a rating of additional ratings from tvshow.nfo.")
					try:
						nforating = round(float(nfoXML.xpath("ratings")[0][0][0].text.replace(',', '.')),1)
						metadata.rating = nforating
						self.DLog("Found first rating in additional ratings: " + str(nforating))
					except:
						self.DLog("Can't read ratings from tvshow.nfo.")
						nforating = 0.0
						pass
				if Prefs['altratings']:
					self.DLog("Searching for additional Ratings...")
					allowedratings = Prefs['ratings']
					if not allowedratings: allowedratings = ""
					addratingsstring = ""
					try:
						addratings = nfoXML.xpath('ratings')
						self.DLog("Trying to read additional ratings from tvshow.nfo.")
					except:
						self.DLog("Can't read additional ratings from tvshow.nfo.")
						pass
					if addratings:
						for addratingXML in addratings:
							for addrating in addratingXML:
								try:
									ratingprovider = str(addrating.attrib['moviedb'])
								except:
									try:
										ratingprovider = str(addrating.attrib['name'])
										addrating = addrating[0]
									except:
										pass
										self.DLog("Skipping additional rating without provider attribute!")
										continue
								ratingvalue = str(addrating.text.replace (',','.'))
								if ratingprovider.lower() in PERCENT_RATINGS:
									ratingvalue = ratingvalue + "%"
								if ratingprovider in allowedratings or allowedratings == "":
									self.DLog("adding rating: " + ratingprovider + ": " + ratingvalue)
									addratingsstring = addratingsstring + " | " + ratingprovider + ": " + ratingvalue
							if addratingsstring != "":
								self.DLog("Putting additional ratings at the " + Prefs['ratingspos'] + " of the summary!")
								if Prefs['ratingspos'] == "front":
									if Prefs['preserverating']:
										metadata.summary = addratingsstring[3:] + self.unescape(" &#9733;\n\n") + metadata.summary
									else:
										metadata.summary = self.unescape("&#9733; ") + addratingsstring[3:] + self.unescape(" &#9733;\n\n") + metadata.summary
								else:
									metadata.summary = metadata.summary + self.unescape("\n\n&#9733; ") + addratingsstring[3:] + self.unescape(" &#9733;")
							else:
								self.DLog("Additional ratings empty or malformed!")
					if Prefs['preserverating']:
						self.DLog("Putting .nfo rating in front of summary!")
						metadata.summary = self.unescape(str(Prefs['beforerating'])) + "{:.1f}".format(nforating) + self.unescape(str(Prefs['afterrating'])) + metadata.summary
						metadata.rating = nforating
					else:
						metadata.rating = nforating
				# Genres
				try:
					genres = nfoXML.xpath('genre')
					metadata.genres.clear()
					[metadata.genres.add(g.strip()) for genreXML in genres for g in genreXML.text.split("/")]
					metadata.genres.discard('')
				except: pass
				# Collections (Set)
				setname = None
				try:
					metadata.collections.clear()
					# trying enhanced set tag name first
					setname = nfoXML.xpath('set')[0].xpath('name')[0].text
					self.DLog('Enhanced set tag found: ' + setname)
				except:
					self.DLog('No enhanced set tag found...')
					pass
				try:
					# fallback to flat style set tag
					if not setname:
						setname = nfoXML.xpath('set')[0].text
						self.DLog('Set tag found: ' + setname)
				except:
					self.DLog('No set tag found...')
					pass
				if setname:
					metadata.collections.add (setname)
					self.DLog('Added Collection from Set tag.')
				# Collections (Tags)
				try:
					tags = nfoXML.xpath('tag')
					[metadata.collections.add(t.strip()) for tag_xml in tags for t in tag_xml.text.split('/')]
					self.DLog('Added Collection(s) from tags.')
				except:
					self.DLog('Error adding Collection(s) from tags.')
					pass
				# Duration
				try:
					sruntime = nfoXML.xpath("durationinseconds")[0].text
					metadata.duration = int(re.compile('^([0-9]+)').findall(sruntime)[0]) * 1000
				except:
					try:
						sruntime = nfoXML.xpath("runtime")[0].text
						duration = int(re.compile('^([0-9]+)').findall(sruntime)[0])
						duration_ms = xbmcnfotv.time_convert (self, duration)
						metadata.duration = duration_ms
						self.DLog("Set Series Episode Duration from " + str(duration) + " in tvshow.nfo file to " + str(duration_ms) + " in Plex.")
					except:
						self.DLog("No Series Episode Duration in tvschow.nfo file.")
						pass

				# Show assets
				if not Prefs['localmediaagent']:
					if Prefs['assetslocation'] == 'local':
						Log("Looking for show assets for %s from local", metadata.title)
						try: self.AssetsLocal(metadata, [path], 'show')
						except Exception, e:
							Log('Error finding show assets for %s from local: %s', metadata.title, str(e))
					else:
						Log("Looking for show assets for %s from url", metadata.title)
						try: self.AssetsLink(nfoXML, metadata, 'show')
						except Exception, e:
							Log('Error finding show assets for %s from url: %s', metadata.title, str(e))

				# Actors
				rroles = []
				metadata.roles.clear()
				for n, actor in enumerate(nfoXML.xpath('actor')):
					newrole = metadata.roles.new()
					try:
						newrole.name = actor.xpath('name')[0].text
					except:
						newrole.name = 'Unknown Name ' + str(n)
						pass
					try:
						role = actor.xpath('role')[0].text
						if role in rroles:
							newrole.role = role + ' ' + str(n)
						else:
							newrole.role = role
						rroles.append (newrole.role)
					except:
						newrole.role = 'Unknown Role ' + str(n)
						pass
					newrole.photo = ''
					athumbloc = Prefs['athumblocation']
					if athumbloc in ['local','global']:
						aname = None
						try:
							try:
								aname = actor.xpath('name')[0].text
							except:
								pass
							if aname:
								aimagefilename = aname.replace(' ', '_') + '.jpg'
								athumbpath = Prefs['athumbpath'].rstrip ('/')
								if not athumbpath == '':
									if athumbloc == 'local':
										localpath = os.path.join (path,'.actors',aimagefilename)
										scheme, netloc, spath, qs, anchor = urlparse.urlsplit(athumbpath)
										basepath = os.path.basename (spath)
										self.DLog ('Searching for additional path parts after: ' + basepath)
										searchpos = path.find (basepath)
										addpos = searchpos + len(basepath)
										addpath = os.path.dirname(path)[addpos:]
										if searchpos != -1 and addpath !='':
											self.DLog ('Found additional path parts: ' + addpath)
										else:
											addpath = ''
											self.DLog ('Found no additional path parts.')
										aimagepath = athumbpath + addpath + '/' + os.path.basename(path) + '/.actors/' + aimagefilename
										if not os.path.isfile(localpath):
											self.DLog ('failed setting ' + athumbloc + ' actor photo: ' + aimagepath)
											aimagepath = None
									if athumbloc == 'global':
										aimagepath = athumbpath + '/' + aimagefilename
										scheme, netloc, spath, qs, anchor = urlparse.urlsplit(aimagepath)
										spath = urllib.quote(spath, '/%')
										qs = urllib.quote_plus(qs, ':&=')
										aimagepathurl = urlparse.urlunsplit((scheme, netloc, spath, qs, anchor))
										response = urllib.urlopen(aimagepathurl).code
										if not response == 200:
											self.DLog ('failed setting ' + athumbloc + ' actor photo: ' + aimagepath)
											aimagepath = None
									if aimagepath:
										newrole.photo = aimagepath
										self.DLog ('success setting ' + athumbloc + ' actor photo: ' + aimagepath)
						except:
							self.DLog ('exception setting local or global actor photo!')
							self.DLog ("Traceback: " + traceback.format_exc())
							pass
					if athumbloc == 'link' or not newrole.photo:
						try:
							newrole.photo = actor.xpath('thumb')[0].text
							self.DLog ('linked actor photo: ' + newrole.photo)
						except:
							self.DLog ('failed setting linked actor photo!')
							pass

				Log("---------------------")
				Log("Series nfo Information")
				Log("---------------------")
				try: Log("ID: " + str(metadata.guid))
				except: Log("ID: -")
				try: Log("Title: " + str(metadata.title))
				except: Log("Title: -")
				try: Log("Sort Title: " + str(metadata.title_sort))
				except: Log("Sort Title: -")
				try: Log("Original: " + str(metadata.original_title))
				except: Log("Original: -")
				try: Log("Rating: " + str(metadata.rating))
				except: Log("Rating: -")
				try: Log("Content: " + str(metadata.content_rating))
				except: Log("Content: -")
				try: Log("Network: " + str(metadata.studio))
				except: Log("Network: -")
				try: Log("Premiere: " + str(metadata.originally_available_at))
				except: Log("Premiere: -")
				try: Log("Tagline: " + str(metadata.tagline))
				except: Log("Tagline: -")
				try: Log("Summary: " + str(metadata.summary))
				except: Log("Summary: -")
				Log("Genres:")
				try: [Log("\t" + genre) for genre in metadata.genres]
				except: Log("\t-")
				Log("Collections:")
				try: [Log("\t" + collection) for collection in metadata.collections]
				except: Log("\t-")
				try: Log("Duration: " + str(metadata.duration // 60000) + ' min')
				except: Log("Duration: -")
				Log("Actors:")
				try: [Log("\t" + actor.name + " > " + actor.role) for actor in metadata.roles]
				except: [Log("\t" + actor.name) for actor in metadata.roles]
				except: Log("\t-")
				Log("---------------------")

		# Grabs the season data
		@parallelize
		def UpdateEpisodes():
			self.DLog("UpdateEpisodes called")
			pageUrl = "http://127.0.0.1:32400/library/metadata/" + media.id + "/children"
			seasonList = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Directory')

			seasons = []
			for seasons in seasonList:
				try: seasonID = seasons.get('key')
				except: pass
				try: season_num = seasons.get('index')
				except: pass

				self.DLog("seasonID : " + path)
				if seasonID.count('allLeaves') == 0:
					self.DLog("Finding episodes")

					pageUrl = "http://127.0.0.1:32400" + seasonID

					episodes = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Video')
					self.DLog("Found " + str(len(episodes)) + " episodes.")

					firstEpisodePath = XML.ElementFromURL(pageUrl).xpath('//Part')[0].get('file')
					seasonPath = os.path.dirname(firstEpisodePath)

					metadata.seasons[season_num].index = int(season_num)

					if not Prefs['localmediaagent']:
						if Prefs['assetslocation'] == 'local':
							Log('Looking for season assets for %s season %s.', metadata.title, season_num)
							try: self.AssetsLocal(metadata.seasons[season_num], [path, seasonPath], 'season')
							except Exception, e: Log("Error finding season assets for %s season %s: %s", metadata.title, season_num, str(e))
						else:
							Log('Looking for season assets for %s season %s from url', metadata.title, season_num)
							try: self.AssetsLink(nfoXML, metadata.seasons[season_num], 'season')
							except Exception, e: Log('Error finding season assets for %s season %s from url: %s', metadata.title, season_num, str(e))

					episodeXML = []
					epnumber = 0
					for episodeXML in episodes:
						ep_key = episodeXML.get('key')
						self.DLog("epKEY: " + ep_key)
						epnumber = epnumber + 1
						ep_num = episodeXML.get('index')
						if (ep_num == None):
							self.DLog("epNUM: Error!")
							ep_num = str(epnumber)
						self.DLog("epNUM: " + ep_num)

						# Get the episode object from the model
						episode = metadata.seasons[season_num].episodes[ep_num]

						# Grabs the episode information
						@task
						def UpdateEpisode(episode=episode, season_num=season_num, ep_num=ep_num, ep_key=ep_key, path=path1):
							self.DLog("UpdateEpisode called for episode (" + str(episode)+ ", " + str(ep_key) + ") S" + str(season_num.zfill(2)) + "E" + str(ep_num.zfill(2)))
							if(ep_num.count('allLeaves') == 0):
								pageUrl = "http://127.0.0.1:32400" + ep_key + "/tree"
								path1 = String.Unquote(XML.ElementFromURL(pageUrl).xpath('//MediaPart')[0].get('file')).encode('utf-8')

								self.DLog('UPDATE: ' + path1)
								filepath = path1.split
								path = os.path.dirname(path1)
								fileExtension = path1.split(".")[-1].lower()

								nfoFile = path1.replace('.'+fileExtension, '.nfo')
								self.DLog("Looking for episode NFO file " + nfoFile)
								if os.path.exists(nfoFile):
									self.DLog("File exists...")
									nfoText = Core.storage.load(nfoFile)
									# strip media browsers <multiepisodenfo> tags
									nfoText = nfoText.replace ('<multiepisodenfo>','')
									nfoText = nfoText.replace ('</multiepisodenfo>','')
									# strip Sick Beard's <xbmcmultiepisodenfo> tags
									nfoText = nfoText.replace ('<xbmcmultiepisode>','')
									nfoText = nfoText.replace ('</xbmcmultiepisode>','')
									# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
									nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
									# remove empty xml tags from nfo
									self.DLog('Removing empty XML tags from tvshows nfo...')
									nfoText = re.sub(r'^\s*<.*/>[\r\n]+', '', nfoText, flags = re.MULTILINE)
									nfoTextLower = nfoText.lower()
									if nfoTextLower.count('<episodedetails') > 0 and nfoTextLower.count('</episodedetails>') > 0:
										self.DLog("Looks like an XBMC NFO file (has <episodedetails>)")
										nfoepc = int(nfoTextLower.count('<episodedetails'))
										nfopos = 1
										multEpTitlePlexPatch = multEpSummaryPlexPatch = ""
										multEpTestPlexPatch = 0
										while nfopos <= nfoepc:
											self.DLog("EpNum: " + str(ep_num) + " NFOEpCount:" + str(nfoepc) +" Current EpNFOPos: " + str(nfopos))
											# Remove URLs (or other stuff) at the end of the XML file
											nfoTextTemp = '%s</episodedetails>' % nfoText.split('</episodedetails>')[nfopos-1]

											# likely an xbmc nfo file
											try: nfoXML = XML.ElementFromString(nfoTextTemp).xpath('//episodedetails')[0]
											except:
												self.DLog('ERROR: Cant parse XML in file: ' + nfoFile)
												return

											# remove remaining empty xml tags
											self.DLog('Removing remaining empty XML Tags from episode nfo...')
											nfoXML = self.RemoveEmptyTags(nfoXML)

											# check ep number
											nfo_ep_num = 0
											try:
												nfo_ep_num = nfoXML.xpath('episode')[0].text
												self.DLog('EpNum from NFO: ' + str(nfo_ep_num))
											except:
												self.DLog('No EpNum from NFO! Assuming: ' + ep_num)
												nfo_ep_num = ep_num
												pass

											# Checks to see user has renamed files so plex ignores multiepisodes and confirms that there is more than on episodedetails
											if not re.search('.s\d{1,3}e\d{1,3}[-]?e\d{1,3}.', path1.lower()) and (nfoepc > 1):
												multEpTestPlexPatch = 1

											# Creates combined strings for Plex MultiEpisode Patch
											if multEpTestPlexPatch and Prefs['multEpisodePlexPatch'] and (nfoepc > 1):
												self.DLog('Multi Episode found: ' + str(nfo_ep_num))
												multEpTitleSeparator = Prefs['multEpisodeTitleSeparator']
												try:
													if nfopos == 1:
														multEpTitlePlexPatch = nfoXML.xpath('title')[0].text
														multEpSummaryPlexPatch = "[Episode #" + str(nfo_ep_num) + " - " + nfoXML.xpath('title')[0].text + "] " + nfoXML.xpath('plot')[0].text
													else:
														multEpTitlePlexPatch = multEpTitlePlexPatch + multEpTitleSeparator + nfoXML.xpath('title')[0].text
														multEpSummaryPlexPatch = multEpSummaryPlexPatch + "\n" + "[Episode #" + str(nfo_ep_num) + " - " + nfoXML.xpath('title')[0].text + "] " + nfoXML.xpath('plot')[0].text
												except: pass
											else:
												if int(nfo_ep_num) == int(ep_num):
													nfoText = nfoTextTemp
													break

											nfopos = nfopos + 1

										if (not multEpTestPlexPatch or not Prefs['multEpisodePlexPatch']) and (nfopos > nfoepc):
											self.DLog('No matching episode in nfo file!')
											return

										# Ep. Title
										if Prefs['multEpisodePlexPatch'] and (multEpTitlePlexPatch != ""):
											self.DLog('using multi title: ' + multEpTitlePlexPatch)
											episode.title = multEpTitlePlexPatch
										else:
											try: episode.title = nfoXML.xpath('title')[0].text
											except:
												self.DLog("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
												return
										# Ep. Content Rating
										try:
											mpaa = nfoXML.xpath('./mpaa')[0].text
											match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
											if match.group('mpaa'):
												content_rating = match.group('mpaa')
											else:
												content_rating = 'NR'
											episode.content_rating = content_rating
										except: pass
										# Ep. Premiere
										try:
											air_string = None
											try:
												self.DLog("Reading aired tag...")
												air_string = nfoXML.xpath("aired")[0].text
												self.DLog("Aired tag is: " + air_string)
											except:
												self.DLog("No aired tag found...")
												pass
											if not air_string:
												try:
													self.DLog("Reading dateadded tag...")
													air_string = nfoXML.xpath("dateadded")[0].text
													self.DLog("Dateadded tag is: " + air_string)
												except:
													self.DLog("No dateadded tag found...")
													pass
											if air_string:
												try:
													if Prefs['dayfirst']:
														dt = parse(air_string, dayfirst=True)
													else:
														dt = parse(air_string)
													episode.originally_available_at = dt
													self.DLog("Set premiere to: " + dt.strftime('%Y-%m-%d'))
												except:
													self.DLog("Couldn't parse premiere: " + air_string)
													pass
										except:
											self.DLog("Exception parsing Ep Premiere: " + traceback.format_exc())
											pass
										# Ep. Summary
										if Prefs['multEpisodePlexPatch'] and (multEpSummaryPlexPatch != ""):
											self.DLog('using multi summary: ' + multEpSummaryPlexPatch)
											episode.summary = multEpSummaryPlexPatch
										else:
											try: episode.summary = nfoXML.xpath('plot')[0].text
											except:
												episode.summary = ""
												pass
										# Ep. Ratings
										try:
											epnforating = round(float(nfoXML.xpath("rating")[0].text.replace(',', '.')),1)
											episode.rating = epnforating
											self.DLog("Episode Rating found: " + str(epnforating))
										except:
											self.DLog("Cant read rating from episode nfo.")
											epnforating = 0.0
											pass
										if Prefs['altratings']:
											self.DLog("Searching for additional episode ratings...")
											allowedratings = Prefs['ratings']
											if not allowedratings: allowedratings = ""
											addepratingsstring = ""
											try:
												addepratings = nfoXML.xpath('ratings')
												self.DLog("Additional episode ratings found: " + str(addeprating))
											except:
												self.DLog("Can't read additional episode ratings from nfo.")
												pass
											if addepratings:
												for addepratingXML in addepratings:
													for addeprating in addepratingXML:
														try:
															epratingprovider = str(addeprating.attrib['moviedb'])
														except:
															pass
															self.DLog("Skipping additional episode rating without moviedb attribute!")
															continue
														epratingvalue = str(addeprating.text.replace (',','.'))
														if epratingprovider.lower() in PERCENT_RATINGS:
															epratingvalue = epratingvalue + "%"
														if epratingprovider in allowedratings or allowedratings == "":
															self.DLog("adding episode rating: " + epratingprovider + ": " + epratingvalue)
															addepratingsstring = addepratingsstring + " | " + epratingprovider + ": " + epratingvalue
												if addratingsstring != "":
													self.DLog("Putting additional episode ratings at the " + Prefs['ratingspos'] + " of the summary!")
													if Prefs['ratingspos'] == "front":
														if Prefs['preserveratingep']:
															episode.summary = addepratingsstring[3:] + self.unescape(" &#9733;\n\n") + episode.summary
														else:
															episode.summary = self.unescape("&#9733; ") + addepratingsstring[3:] + self.unescape(" &#9733;\n\n") + episode.summary
													else:
														episode.summary = episode.summary + self.unescape("\n\n&#9733; ") + addepratingsstring[3:] + self.unescape(" &#9733;")
												else:
													self.DLog("Additional episode ratings empty or malformed!")
											if Prefs['preserveratingep']:
												self.DLog("Putting Ep .nfo rating in front of summary!")
												episode.summary = self.unescape(str(Prefs['beforeratingep'])) + "{:.1f}".format(epnforating) + self.unescape(str(Prefs['afterratingep'])) + episode.summary
												episode.rating = epnforating
											else:
												episode.rating = epnforating
										# Ep. Producers / Writers / Guest Stars(Credits)
										try:
											credit_string = None
											credits = nfoXML.xpath('credits')
											episode.producers.clear()
											episode.writers.clear()
											episode.guest_stars.clear()
											for creditXML in credits:
												for credit in creditXML.text.split("/"):
													credit_string = credit.strip()
													self.DLog ("Credit String: " + credit_string)
													if re.search ("(Producer)", credit_string, re.IGNORECASE):
														credit_string = re.sub ("\(Producer\)","",credit_string,flags=re.I).strip()
														self.DLog ("Credit (Producer): " + credit_string)
														episode.producers.new().name = credit_string
														continue
													if re.search ("(Guest Star)", credit_string, re.IGNORECASE):
														credit_string = re.sub ("\(Guest Star\)","",credit_string,flags=re.I).strip()
														self.DLog ("Credit (Guest Star): " + credit_string)
														episode.guest_stars.new().name = credit_string
														continue
													if re.search ("(Writer)", credit_string, re.IGNORECASE):
														credit_string = re.sub ("\(Writer\)","",credit_string,flags=re.I).strip()
														self.DLog ("Credit (Writer): " + credit_string)
														episode.writers.new().name = credit_string
														continue
													self.DLog ("Unknown Credit (adding as Writer): " + credit_string)
													episode.writers.new().name = credit_string
										except:
											self.DLog("Exception parsing Credits: " + traceback.format_exc())
											pass
										# Ep. Directors
										try:
											directors = nfoXML.xpath('director')
											episode.directors.clear()
											for directorXML in directors:
												for director in directorXML.text.split("/"):
													director_string = director.strip()
													self.DLog ("Director: " + director)
													episode.directors.new().name = director
										except:
											self.DLog("Exception parsing Director: " + traceback.format_exc())
											pass
										# Ep. Duration
										try:
											self.DLog ("Trying to read <durationinseconds> tag from episodes .nfo file...")
											fileinfoXML = XML.ElementFromString(nfoText).xpath('fileinfo')[0]
											streamdetailsXML = fileinfoXML.xpath('streamdetails')[0]
											videoXML = streamdetailsXML.xpath('video')[0]
											eruntime = videoXML.xpath("durationinseconds")[0].text
											eduration_ms = int(re.compile('^([0-9]+)').findall(eruntime)[0]) * 1000
											episode.duration = eduration_ms
										except:
											try:
												self.DLog ("Fallback to <runtime> tag from episodes .nfo file...")
												eruntime = nfoXML.xpath("runtime")[0].text
												eduration = int(re.compile('^([0-9]+)').findall(eruntime)[0])
												eduration_ms = xbmcnfotv.time_convert (self, eduration)
												episode.duration = eduration_ms
											except:
												episode.duration = metadata.duration if metadata.duration else None
												self.DLog ("No Episode Duration in episodes .nfo file.")
												pass
										try:
											if (eduration_ms > 0):
												eduration_min = int(round (float(eduration_ms) / 1000 / 60))
												Dict[duration_key][eduration_min] = Dict[duration_key][eduration_min] + 1
										except:
											pass

										if not Prefs['localmediaagent']:
											multEpisode = (nfoepc > 1) and (not Prefs['multEpisodePlexPatch'] or not multEpTestPlexPatch)

											episodeMedia = media.seasons[season_num].episodes[ep_num].items[0]
											path = os.path.dirname(episodeMedia.parts[0].file)
											if Prefs['assetslocation'] == 'local':
												Log('Looking for episode assets %s for %s season %s.', ep_num, metadata.title, season_num)
												try: self.AssetsLocal(episode, [path], 'episode', episodeMedia.parts, multEpisode)
												except Exception, e: Log('Error finding episode assets %s for %s season %s: %s', ep_num, metadata.title, season_num,str(e))
											else:
												Log('Looking for episode assets for %s season %s from url', metadata.title, season_num)
												try:
													thumb = nfoXML.xpath('thumb')[0]
													Log('Trying to get thumbnail for episode %s for %s season %s from url.', ep_num,  metadata.title, season_num)
													try:
														episode.thumbs[thumb.text] = Proxy.Media(HTTP.Request(thumb.text))
														episode.thumbs.validate_keys([thumb.text])
														Log('Found episode thumbnail from url')
													except Exception as e:
														Log('Error download episode thumbnail %s for %s season %s from url: %s', ep_num,  metadata.title, season_num, str(e))
												except Exception, e:
													Log('Error finding episode thumbnail %s for %s season %s from url: %s', ep_num,  metadata.title, season_num, str(e))

										Log("---------------------")
										Log("Episode (S"+season_num.zfill(2)+"E"+ep_num.zfill(2)+") nfo Information")
										Log("---------------------")
										try: Log("Title: " + str(episode.title))
										except: Log("Title: -")
										try: Log("Content: " + str(episode.content_rating))
										except: Log("Content: -")
										try: Log("Rating: " + str(episode.rating))
										except: Log("Rating: -")
										try: Log("Premiere: " + str(episode.originally_available_at))
										except: Log("Premiere: -")
										try: Log("Summary: " + str(episode.summary))
										except: Log("Summary: -")
										Log("Writers:")
										try: [Log("\t" + writer.name) for writer in episode.writers]
										except: Log("\t-")
										Log("Directors:")
										try: [Log("\t" + director.name) for director in episode.directors]
										except: Log("\t-")
										try: Log("Duration: " + str(episode.duration // 60000) + ' min')
										except: Log("Duration: -")
										Log("---------------------")
									else:
										Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfoFile)

		# Final Steps
		duration_min = 0
		duration_string = ""
		if not metadata.duration:
			try:
				duration_min = Dict[duration_key].index(max(Dict[duration_key]))
				for d in Dict[duration_key]:
					if (d != 0):
						duration_string = duration_string + "(" + str(Dict[duration_key].index(d)) + "min:" + str(d) + ")"
			except:
				self.DLog("Error accessing duration_key in dictionary!")
				pass
			self.DLog("Episode durations are: " + duration_string)
			metadata.duration = duration_min * 60 * 1000
			self.DLog("Set Series Episode Runtime to median of all episodes: " + str(metadata.duration) + " (" + str (duration_min) + " minutes)")
		else:
			self.DLog("Series Episode Runtime already set! Current value is:" + str(metadata.duration))
		Dict.Reset()
