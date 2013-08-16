# xbmc-nfo importer
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
#
import os, re, time, datetime

class xbmcnfo(Agent.TV_Shows):
	name = 'XBMC TV .nfo Importer'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]
	accepts_from = ['com.plexapp.agents.localmedia']

##### helper functions #####
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
			Log("Trying " + pathfn)
			if not os.path.exists(pathfn):
				continue
			else:
				Log("Found " + ftype + " file " + pathfn)
				return pathfn
		else:
			Log("No " + ftype + " file found! Aborting!")

##### search function #####
	def search(self, results, media, lang):
		Log("++++++++++++++++++++++++")
		Log("Entering search function")
		Log("++++++++++++++++++++++++")

		parse_date = lambda s: Datetime.ParseDate(s).date()
		Log(media.primary_metadata)
		path1 = os.path.dirname(String.Unquote(media.filename).encode('utf-8'))
		Log(path1)
		path = os.path.dirname(path1)
		nfoName = path + "/tvshow.nfo"
		Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			nfoName = path1 + "/tvshow.nfo"
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
			# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&([^a-zA-Z#])', r'&amp;\1', nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</tvshow>' % nfoText.split('</tvshow>')[0]
				
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
		Log('scraped results: ' + tvshowname + ' | year = ' + str(year) + ' | id = ' + tvshowid)

##### update Function #####
	def update(self, metadata, media, lang):
		Log("++++++++++++++++++++++++")
		Log("Entering update function")
		Log("++++++++++++++++++++++++")

		Dict.Reset()
		id = media.id
		duration_key = 'duration_'+id
		Dict[duration_key] = [0] * 200
		Log('Update called for TV Show with id = ' + id)
		try: path1 = os.path.dirname(media.items[0].parts[0].file)
		except:
			pageUrl = "http://localhost:32400/library/metadata/" + id + "/tree"
			nfoXML = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
			path1 = os.path.dirname(String.Unquote(nfoXML.get('file')))
		path = os.path.dirname(path1)
		parse_date = lambda s: Datetime.ParseDate(s).date()
		
		nfoName = path + "/tvshow.nfo"
		Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			nfoName = path1 + "/tvshow.nfo"
			Log('Looking for TV Show NFO file at ' + nfoName)
		if not os.path.exists(nfoName):
			path = os.path.dirname(path1)

		posterNames = []
		posterNames.append (path + "/poster.jpg")
		posterNames.append (path + "/folder.jpg")
		posterNames.append (path + "/show.jpg")
		posterNames.append (path + "/season-all-poster.jpg")

		# check possible poster file locations
		posterFilename = self.checkFilePaths (posterNames, 'poster')

		if posterFilename:
			posterData = Core.storage.load(posterFilename)
			metadata.posters['poster.jpg'] = Proxy.Media(posterData)
			Log('Found poster image at ' + posterFilename)

		bannerNames = []
		bannerNames.append (path + "/banner.jpg")
		bannerNames.append (path + "/folder-banner.jpg")

		# check possible banner file locations
		bannerFilename = self.checkFilePaths (bannerNames, 'banner')

		if bannerFilename:
			bannerData = Core.storage.load(bannerFilename)
			metadata.banners['banner.jpg'] = Proxy.Media(bannerData)
			Log('Found banner image at ' + bannerFilename)

		fanartNames = []

		fanartNames.append (path + "/fanart.jpg")
		fanartNames.append (path + "/art.jpg")
		fanartNames.append (path + "/backdrop.jpg")
		fanartNames.append (path + "/background.jpg")

		# check possible fanart file locations
		fanartFilename = self.checkFilePaths (fanartNames, 'fanart')

		if fanartFilename:
			fanartData = Core.storage.load(fanartFilename)
			metadata.art['fanart.jpg'] = Proxy.Media(fanartData)
			Log('Found fanart image at ' + fanartFilename)

		themeNames = []

		themeNames.append (path + "/theme.mp3")

		# check possible theme file locations
		themeFilename = self.checkFilePaths (themeNames, 'theme')

		if themeFilename:
			themeData = Core.storage.load(themeFilename)
			metadata.themes['theme.mp3'] = Proxy.Media(themeData)
			Log('Found theme music ' + themeFilename)

		if not os.path.exists(nfoName):
			Log("Couldn't find a tvshow.nfo file; will use the folder name as the TV show title:")
			path = os.path.dirname(path1)
			metadata.title = os.path.basename(path)
			Log("Using tvshow.title = " + metadata.title)
		else:
			nfoFile = nfoName
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&([^a-zA-Z#])', r'&amp;\1', nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<tvshow') > 0 and nfoTextLower.count('</tvshow>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</tvshow>' % nfoText.split('</tvshow>')[0]

				#likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//tvshow')[0]
				except:
					Log('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return
				#tv show name
				try: metadata.title=nfoXML.xpath("title")[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				#tv show original name
				try: metadata.original_title = nfoXML.xpath('./originaltitle')[0].text
				except: pass
				#tv show summary
				try: metadata.summary=nfoXML.xpath("plot")[0].text
				except: pass
				#tv show tagline
				try: metadata.tagline = nfoXML.findall("tagline")[0].text
				except: pass
				#tv show year and first Aired
				try: metadata.originally_available_at=parse_date(nfoXML.xpath("premiered")[0].text) #metadata.originally_available_at=nfoXML.xpath("aired")[0].text
				except: pass
				#tv show rating
				try: metadata.rating=float(nfoXML.xpath("rating")[0].text.replace(',','.'))
				except: pass
				#tv show content rating
				try: metadata.content_rating=nfoXML.xpath("mpaa")[0].text
				except: pass
				#tv show network
				try: metadata.studio=nfoXML.xpath("studio")[0].text
				except: pass
				#tv show duration
				try:
					sruntime=nfoXML.xpath("runtime")[0].text
					duration = int(re.compile('^([0-9]+)').findall(sruntime)[0])
					duration_ms = xbmcnfo.time_convert (self, duration)
					metadata.duration = duration_ms
					Log("Set Series Episode Duration from " + str(duration) + " in tvshow.nfo file to " + str(duration_ms) + " in Plex.")
				except:
					metadata.duration = 0
					Log("No Series Episode Duration in tvschow.nfo file.")
					pass
				#set/collections
				try:
					set_ = nfoXML.xpath('./set')[0].text
					metadata.collections.clear()
					metadata.collections.add(set_)
				except: pass
				#genre, cant see mulltiple only sees string not seperate genres
				try:
					genres = nfoXML.xpath('./genre')
					metadata.genres.clear()
					for genreXML in genres:
						gs = genreXML.text.split("/")
						if gs != "":
							for g in gs:
								metadata.genres.add(g.strip())
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
					
					firstEpisodePath = XML.ElementFromURL(pageUrl).xpath('//Part')[0].get('file')
					seasonPath = os.path.dirname(firstEpisodePath)
					seasonFilenameFolderJpg = seasonPath.replace(path+'\\','') + '/' + 'folder.jpg'
					seasonPathFilenameFolderJpg = path + '/' + seasonFilenameFolderJpg
					Log("Found poster '" + seasonFilenameFolderJpg + "' - path '" + seasonPathFilenameFolderJpg + "' -CR.")
					if(int(season_num) == 0):
						seasonFilenameEden = 'season-specials.tbn'
					else:
						seasonFilenameEden = 'season%(number)02d.tbn' % {"number": int(season_num)}
					seasonPathFilenameEden = path + '/' + seasonFilenameEden
					if(int(season_num) == 0):
						seasonFilenameFrodo = 'season-specials-poster.jpg'
					else:
						seasonFilenameFrodo = 'season%(number)02d-poster.jpg' % {"number": int(season_num)}
					seasonPathFilenameFrodo = path + '/' + seasonFilenameFrodo
					seasonFilename = ""
					seasonPathFilename = ""
					if os.path.exists(seasonPathFilenameEden):
						seasonFilename = seasonFilenameEden
						seasonPathFilename = seasonPathFilenameEden
					elif os.path.exists(seasonPathFilenameFrodo):
						seasonFilename = seasonFilenameFrodo
						seasonPathFilename = seasonPathFilenameFrodo
					elif os.path.exists(seasonPathFilenameFolderJpg):
						seasonFilename = seasonFilenameFolderJpg
						seasonPathFilename = seasonPathFilenameFolderJpg
					if seasonPathFilename:
						seasonData = Core.storage.load(seasonPathFilename)
						metadata.seasons[season_num].posters[seasonFilename] = Proxy.Media(seasonData)
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
							Log("UpdateEpisode called for episode S" + str(season_num.zfill(2)) + "E" + str(ep_num.zfill(2)))
							if(ep_num.count('allLeaves') == 0):
								pageUrl="http://localhost:32400" + ep_key + "/tree"
								path1 = XML.ElementFromURL(pageUrl).xpath('//MediaPart')[0].get('file')
								Log('UPDATE: ' + path1)
								filepath=path1.split
								path = os.path.dirname(path1)
								fileExtension = path1.split(".")[-1].lower()

								nfoFile = path1.replace('.'+fileExtension, '.nfo')
								Log("Looking for episode NFO file " + nfoFile)
								if os.path.exists(nfoFile):
									Log("File exists...")
									nfoText = Core.storage.load(nfoFile)
									# work around failing XML parses for things with &'s in them. This may need to go farther than just &'s....
									nfoText = re.sub(r'&([^a-zA-Z#])', r'&amp;\1', nfoText)
									nfoTextLower = nfoText.lower()
									if nfoTextLower.count('<episodedetails') > 0 and nfoTextLower.count('</episodedetails>') > 0:
										# Remove URLs (or other stuff) at the end of the XML file
										nfoText = '%s</episodedetails>' % nfoText.split('</episodedetails>')[0]

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
												air_date = time.strptime(nfoXML.xpath("aired")[0].text, "%d %B %Y")
											except:
												air_date = time.strptime(nfoXML.xpath("aired")[0].text, "%Y-%m-%d")
											if air_date:
												episode.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(air_date)).date()
										except: pass
										#rating
										try: episode.rating = float(nfoXML.xpath('./rating')[0].text.replace(',','.'))
										except: pass
										#content rating
										try: episode.content_rating = nfoXML.xpath('./mpaa')[0].text
										except: pass
										#director
										try: 
											directors = nfoXML.xpath('./director')
											episode.directors.clear()
											for directorXML in directors:
												ds = directorXML.text.split("/")
												if ds != "":
													for d in ds:
														episode.directors.add(d)
										except: pass
										#writers/credits
										try: 
											credits = nfoXML.xpath('./credits')
											episode.writers.clear()
											for creditXML in credits:
												writer = creditXML.text
												episode.writers.add(writer)
										except: pass
										#studio
										try: episode.studio = nfoXML.findall("studio")[0].text
										except: pass
										#runtime
										try:
											eruntime = nfoXML.findall("runtime")[0].text
											eduration = int(re.compile('^([0-9]+)').findall(eruntime)[0])
											eduration_ms = xbmcnfo.time_convert (self, eduration)
											episode.duration = eduration_ms
											if (eduration > 0):
												eduration_min = int(round (float(eduration_ms) / 1000 / 60))
												Dict[duration_key][eduration_min] = Dict[duration_key][eduration_min] + 1
										except:
											eduration = eduration_min = eduration_ms = 0
											Log ("No Episode Duration in episodes .nfo file.")
											pass
										
										thumbPathFilenameDLNA = nfoFile.replace('.nfo', '.jpg')
										thumbFilenameDLNA = thumbPathFilenameDLNA.replace(path+'\\', '')
										Log("Found thumb '" + thumbFilenameDLNA + "' - path '" + thumbPathFilenameDLNA + "' -CR.")
										thumbPathFilenameEden = nfoFile.replace('.nfo', '.tbn')
										thumbFilenameEden = thumbPathFilenameEden.replace(path+'\\', '')
										thumbPathFilenameFrodo = nfoFile.replace('.nfo', '-thumb.jpg')
										thumbFilenameFrodo = thumbPathFilenameFrodo.replace(path+'\\', '')
										thumbPathFilename = ""
										thumbFilename = ""
										
										if os.path.exists(thumbPathFilenameEden):
											thumbFilename = thumbFilenameEden
											thumbPathFilename = thumbPathFilenameEden
										elif os.path.exists(thumbPathFilenameFrodo):
											thumbFilename = thumbFilenameFrodo
											thumbPathFilename = thumbPathFilenameFrodo
										elif os.path.exists(thumbPathFilenameDLNA):
											thumbFilename = thumbFilenameDLNA
											thumbPathFilename = thumbPathFilenameDLNA
										if thumbPathFilename:
											thumbData = Core.storage.load(thumbPathFilename)
											episode.thumbs[thumbFilename] = Proxy.Media(thumbData)
											Log("Found episode thumb " + thumbPathFilename)
										else:
											m = nfoXML.findall("episodedetails/thumb")
											if len(m) > 0:
												thumbURL = m[0].text
												Log("Found episode thumb " + thumbURL)
												try: episode.thumbs[thumbURL] = Proxy.Media(HTTP.Request(thumbURL))
												except: pass
										try:
												ep_summary = episode.summary.replace("\n", " ")
										except:
												ep_summary = episode.summary
										indent = '{:>61}'#.format('')
										logtext = ("" +
										"+++++++++++++++++++++++++++++++++\n" + indent +
										"TV Episode S" + season_num.zfill(2) + "E" + ep_num.zfill(2) + " nfo Information\n" + indent +
										"---------------------------------\n" + indent +
										"Title: " + str(episode.title) + "\n" + indent +
										"Summary: " + str(ep_summary) + "\n" + indent +
										"Year: " + str(episode.originally_available_at) + "\n" + indent +
										"IMDB rating: " + str(episode.rating) + "\n" + indent +
										"Episode .nfo: " + str(eduration) + "\n" + indent +
										"Episode ms: " + str(eduration_ms) + "\n" + indent +
										"Episode min: " + str(eduration_min) + "\n" + indent +
										"+++++++++++++++++++++++++++++++++")
										Log(logtext)
									else:
										Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfoFile)

		# Final Steps
		if metadata.duration == 0:
			try:
				duration_min = Dict[duration_key].index(max(Dict[duration_key]))
				metadata.duration = duration_min * 60 * 1000
				Log("Set Series Episode Runtime to median of all episodes: " + str(metadata.duration) + " (" + str (duration_min) + " minutes)")
			except:
				Log("Couldn't set Series Episode Runtime to median!")
				pass
		else:
			Log("Series Episode Runtime already set!")
		Dict.Reset()
