# xbmc-nfo importer
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
#
import os, re, time, datetime

class xbmcnfo(Agent.TV_Shows):
	name = 'XBMC TV .nfo Importer'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]
	
	def search(self, results, media, lang):
		Log("Searching")
	
		parse_date = lambda s: Datetime.ParseDate(s).date()
		pageUrl="http://localhost:32400/library/metadata/" + media.id + "/tree"
		page=HTTP.Request(pageUrl)
		Log(media.primary_metadata)
		Log(XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MetadataItem'))
		nfoXML = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
		path1 = String.Unquote(nfoXML.get('file')).encode('utf-8')
		Log(path1)
		path = os.path.dirname(path1)
		nfoName = path + "/tvshow.nfo"
		Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			path = os.path.dirname(path)
			nfoName = path + "/tvshow.nfo"
			Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			path = os.path.dirname(path)
			nfoName = path + "/tvshow.nfo"
			Log('Looking for TV Show NFO file at ' + nfoName)

		tvshowid = media.id
		year = 0
		tvshowname = None

		if not os.path.exists(nfoName):
			Log("Couldn't find a tvshow.nfo file; will use the folder name as the TV show title:")
			path = os.path.dirname(path1)
			tvshowname = os.path.basename(path)
			Log("Using tvshow.title = " + tvshowname)
		else:
			nfoFile = nfoName
			Log("Found nfo file at " + nfoFile)
			nfoText = Core.storage.load(nfoFile)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					Log('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return
				Log(nfoXML.xpath("title"))
				#tv show name
				try: tvshowname=nfoXML.xpath("title")[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				#tv show name
				try: year=parse_date(nfoXML.xpath("premiered")[0].text).year
				except: pass
				#tv tv show id
				try: tvshowid=nfoXML.xpath("id")[0].text
				except:
					# if tv show id doesn't exist, create
					# one based on hash of tvshowname
					ord3 = lambda x : '%.3d' % ord(x) 
					tvshowid=int(''.join(map(ord3, tvshowname)))
					tvshowid=str(abs(hash(int(tvshowid))))
				Log('Show name: ' + tvshowname)
				Log('Show ID: ' + tvshowid)
				Log('Year: ' + str(year))

		results.Append(MetadataSearchResult(id=tvshowid, name=tvshowname, year=year, lang=lang, score=100))

		for result in results:
			Log('scraped results: ' + result.name + ' | year = ' + str(result.year) + ' | id = ' + result.id + '| score = ' + str(result.score))
	
	def update(self, metadata, media, lang):
		id = media.id
		Log('Update called for TV Show with id = ' + id)
		pageUrl = "http://localhost:32400/library/metadata/" + id + "/tree"
		page = HTTP.Request(pageUrl)
		xml = XML.ElementFromURL(pageUrl)
		#Log('xml = ' + XML.StringFromElement(xml))
		nfoXML = xml.xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
		path1 = String.Unquote(nfoXML.get('file'))
		path = os.path.dirname(path1)
		parse_date = lambda s: Datetime.ParseDate(s).date()
		
		nfoName = path + "/tvshow.nfo"
		Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			path = os.path.dirname(path)
			nfoName = path + "/tvshow.nfo"
			Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			path = os.path.dirname(path)
			nfoName = path + "/tvshow.nfo"
			Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			path = os.path.dirname(path1)

		posterFilename = ""
		if os.path.exists(path + "/../season-all-poster.jpg"):
			posterFilename = path + "/../season-all-poster.jpg"
		if os.path.exists(path + "/season-all-poster.jpg"):
			posterFilename = path + "/season-all-poster.jpg"
		if os.path.exists(path + "/../folder.jpg"):
			posterFilename = path + "/../folder.jpg"
		if os.path.exists(path + "/folder.jpg"):
			posterFilename = path + "/folder.jpg"
		if os.path.exists(path + "/../poster.jpg"):
			posterFilename = path + "/../poster.jpg"
		if os.path.exists(path + "/poster.jpg"):
			posterFilename = path + "/poster.jpg"
		if posterFilename:
			posterData = Core.storage.load(posterFilename)
			metadata.posters['poster.jpg'] = Proxy.Media(posterData)
			Log('Found poster image at ' + posterFilename)

		bannerFilename = ""
		if os.path.exists(path + "/../folder-banner.jpg"):
			bannerFilename = path + "/../folder-banner.jpg"
		if os.path.exists(path + "/folder-banner.jpg"):
			bannerFilename = path + "/folder-banner.jpg"
		if os.path.exists(path + "/../banner.jpg"):
			bannerFilename = path + "/../banner.jpg"
		if os.path.exists(path + "/banner.jpg"):
			bannerFilename = path + "/banner.jpg"
		if bannerFilename:
			bannerData = Core.storage.load(bannerFilename)
			metadata.banners['banner.jpg'] = Proxy.Media(bannerData)
			Log('Found banner image at ' + bannerFilename)

		fanartFilename = ""
		if os.path.exists(path + "/../fanart.jpg"):
			fanartFilename = path + "/../fanart.jpg"
		if os.path.exists(path + "/fanart.jpg"):
			fanartFilename = path + "/fanart.jpg"
		if fanartFilename:
			fanartData = Core.storage.load(fanartFilename)
			metadata.banners['fanart.jpg'] = Proxy.Media(fanartData)
			Log('Found fanart image at ' + fanartFilename)

		if not os.path.exists(nfoName):
			Log("Couldn't find a tvshow.nfo file; will use the folder name as the TV show title:")
			path = os.path.dirname(path1)
			metadata.title = os.path.basename(path)
			Log("Using tvshow.title = " + metadata.title)
		else:
			nfoFile = nfoName
			nfoText = Core.storage.load(nfoFile)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					Log('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return
				#Log(nfoXML.xpath("title"))
				#tv show name
				try: metadata.title=nfoXML.xpath("title")[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				#tv show year and first Aired
				try: metadata.originally_available_at=parse_date(nfoXML.xpath("premiered")[0].text) #metadata.originally_available_at=nfoXML.xpath("aired")[0].text
				except: pass
				#tv show summary
				try: metadata.summary=nfoXML.xpath("plot")[0].text
				except: pass
				#tv show content rating
				try: metadata.content_rating=nfoXML.xpath("mpaa")[0].text
				except: pass
				#tv show rating
				try: metadata.rating=nfoXML.xpath("rating")[0].text
				except: pass
				#tv show network
				try: metadata.studio=nfoXML.xpath("studio")[0].text
				except: pass
				Log('Title: ' + metadata.title)
				if metadata.originally_available_at:
					Log('Aired: ' + str(metadata.originally_available_at.year) + '-' + str(metadata.originally_available_at.month) + '-' + str(metadata.originally_available_at.day))

				#actors
				metadata.roles.clear()
				for actor in nfoXML.findall('./actor'):
					role = metadata.roles.new()
					try: role.role = actor.xpath("role")[0].text
					except: pass
					try: role.actor = actor.xpath("name")[0].text
					except: pass
					try: role.photo = actor.xpath("thumb")[0].text
					except: pass
					#if role.photo and role.photo != 'None' and role.photo != '':
						#data = HTTP.Request(actor.xpath("thumb")[0].text)
						#Log('Added Thumbnail for: ' + role.actor)

		# Grabs the season data
		@parallelize
		def UpdateEpisodes():
			Log("UpdateEpisodes called")
			pageUrl="http://localhost:32400/library/metadata/" + media.id + "/children"
			seasonList = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Directory')

			seasons=[]
			for seasons in seasonList:
				try: seasonID=seasons.get('key')
				except: pass
				try: season_num=seasons.get('index')
				except: pass
				
				Log("seasonID : " + path)
				if seasonID.count('allLeaves') == 0:
					Log("Finding episodes")

					pageUrl="http://localhost:32400" + seasonID

					episodes = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/Video')
					Log("Found " + str(len(episodes)) + " episodes.")
					
					if(int(season_num) == 0):
						seasonFileNameEden = 'season-specials.tbn'
					else:
						seasonFileNameEden = 'season%(number)02d.tbn' % {"number": int(season_num)}
					seasonPathFilenameEden = path + '/' + seasonFileNameEden
					if(int(season_num) == 0):
						seasonFileNameFrodo = 'season-specials-poster.jpg'
					else:
						seasonFileNameFrodo = 'season%(number)02d-poster.jpg' % {"number": int(season_num)}
					seasonPathFilenameFrodo = path + '/' + seasonFileNameFrodo
					seasonFilename = ""
					seasonPathFilename = ""
					if os.path.exists(seasonPathFilenameEden):
						seasonFilename = seasonFilenameEden
						seasonPathFilename = seasonPathFilenameEden
					if os.path.exists(seasonPathFilenameFrodo):
						seasonFilename = seasonFilenameFrodo
						seasonPathFilename = seasonPathFilenameFrodo
					if seasonPathFilename:
						seasonData = Core.storage.load(seasonPathFilename)
						metadata.seasons[season_num].posters[seasonFileName] = Proxy.Media(seasonData)
						Log('Found season image at ' + seasonPathFilename)
					episodeXML = []
					for episodeXML in episodes:
						ep_num = episodeXML.get('index')
						ep_key = episodeXML.get('key')
		
						Log("Found episode with key: " + ep_key)
	
						# Get the episode object from the model
						episode = metadata.seasons[season_num].episodes[ep_num]				

						# Grabs the episode information
						@task
						def UpdateEpisode(episode=episode, season_num=season_num, ep_num=ep_num, ep_key=ep_key, path=path1):
							Log("UpdateEpisode called for episode S" + str(season_num) + "E" + str(ep_num))
							if(ep_num.count('allLeaves') == 0):
								pageUrl="http://localhost:32400" + ep_key + "/tree"
								path1 = XML.ElementFromURL(pageUrl).xpath('//MediaPart')[0].get('file')
								Log('UPDATE: ' + path1)
								filepath=path1.split
								path = os.path.dirname(path1)
								id=ep_num
								fileExtension = path1.split(".")[-1].lower()

								nfoFile = path1.replace('.'+fileExtension, '.nfo')
								Log("Looking for episode NFO file " + nfoFile)
								if os.path.exists(nfoFile):
									Log("File exists...")
									nfoText = Core.storage.load(nfoFile)
									nfoTextLower = nfoText.lower()
									if nfoTextLower.count('<episodedetails') > 0 and nfoTextLower.count('</episodedetails>') > 0:
										Log("Looks like an XBMC NFO file (has <episodedetails>)")
										#likely an xbmc nfo file
										try: nfoXML = XML.ElementFromString(nfoText).xpath('//episodedetails')[0]
										except:
											Log('ERROR: Cant parse XML in file: ' + nfoFile)
											return

										#title
										try: episode.title = nfoXML.xpath('./title')[0].text
										except: pass
										#summary
										try: episode.summary = nfoXML.xpath('./plot')[0].text
										except: pass			
										#year
										try:
											try:
												air_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%d %B %Y")
											except:
												air_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%Y-%m-%d")
											if air_date:
												episode.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(air_date)).date()
										except: pass
										#content rating
										try: episode.content_rating = nfoXML.xpath('./mpaa')[0].text
										except: pass
										#studio
										try: episode.studio = nfoXML.findall("studio")[0].text
										except: pass
										#airdate
										try:
											runtime = nfoXML.findall("runtime")[0].text
											episode.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000 # ms
										except: pass

										thumbFilenameEden = nfoFile.replace('.nfo', '.tbn')
										thumbFilenameFrodo = nfoFile.replace('.nfo', '-thumb.jpg')
										thumbFilename = ""
										if os.path.exists(thumbFilenameEden):
											thumbFilename = thumbFilenameEden
										if os.path.exists(thumbFilenameFrodo):
											thumbFilename = thumbFilenameFrodo
										if thumbFilename:
											Log("Found episode thumb " + thumbFilename)
											episode.thumbs[thumbFilename] = Proxy.Media(Core.storage.load(thumbFilename))
										else:
											m = nfoXML.findall("episodedetails/thumb")
											if len(m) > 0:
												thumbURL = m[0].text
												Log("Found episode thumb " + thumbURL)
												try: episode.thumbs[thumbURL] = Proxy.Media(HTTP.Request(thumbURL))
												except: pass

										Log("++++++++++++++++++++++++")
										Log("TV Episode nfo Information")
										Log("------------------------")
										Log("Title: " + str(episode.title))
										Log("Summary: " + str(episode.summary))
										Log("Year: " + str(episode.originally_available_at))
										Log("IMDB rating: " + str(episode.rating))
										# Log("Actors")
										# for r in episode.roles:
										#	Log("Actor: " + r.actor + " | Role: " + r.role)
										Log("++++++++++++++++++++++++")
									else:
										Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfoFile)
