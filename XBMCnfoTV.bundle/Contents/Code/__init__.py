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
		Log(media.primary_metadata)
		path1 = String.Unquote(media.filename).encode('utf-8')
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

	def update(self, metadata, media, lang):
		Dict.Reset()
		id = media.id
		duration_key = 'duration_'+id
		epcount_key = 'epcount_'+id
		Dict[duration_key] = 0
		Dict[epcount_key] = 0
		Log('Update called for TV Show with id = ' + id)
		try: path1 = media.items[0].parts[0].file
		except:
			pageUrl = "http://localhost:32400/library/metadata/" + id + "/tree"
			nfoXML = XML.ElementFromURL(pageUrl).xpath('//MediaContainer/MetadataItem/MetadataItem/MetadataItem/MediaItem/MediaPart')[0]
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
			metadata.art['fanart.jpg'] = Proxy.Media(fanartData)
			Log('Found fanart image at ' + fanartFilename)

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
					if os.path.exists(seasonPathFilenameFrodo):
						seasonFilename = seasonFilenameFrodo
						seasonPathFilename = seasonPathFilenameFrodo
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
										#runtime
										try:
											runtime = nfoXML.findall("runtime")[0].text
											duration = int(re.compile('^([0-9]+)').findall(runtime)[0])
											if (duration <= 2):
												duration = duration * 60 * 60 * 1000 #h to ms
											elif (duration <= 120):
												duration = duration * 60 * 1000 #m to ms
											elif (duration <= 7200):
												duration = duration * 1000 #s to ms
											Dict[duration_key] = Dict[duration_key] + duration
											if (duration > 0):
												Dict[epcount_key] = Dict[epcount_key] + 1
											else:
												Log ("ID:" + str(id) + " S" + str (season_num) + "E" + str (ep_num) + ": Runtime 0 in nfo!")
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
										try:
												ep_summary = episode.summary.replace("\n", " ")
										except:
												ep_summary = episode.summary
										indent = '{:>61}'.format('')
										logtext = ("" +
										"+++++++++++++++++++++++++++++++++\n" + indent +
										"TV Episode S" + season_num.zfill(2) + "E" + ep_num.zfill(2) + " nfo Information\n" + indent +
										"---------------------------------\n" + indent +
										"Title: " + str(episode.title) + "\n" + indent +
										"Summary: " + str(ep_summary) + "\n" + indent +
										"Year: " + str(episode.originally_available_at) + "\n" + indent +
										"IMDB rating: " + str(episode.rating) + "\n" + indent +
										"Runtime (NFO Value): " + str(runtime) + "\n" + indent +
										"+++++++++++++++++++++++++++++++++")
										Log(logtext)
									else:
										Log("ERROR: <episodedetails> tag not found in episode NFO file " + nfoFile)

		# Final Steps
		try:
			metadata.duration = int(Dict[duration_key] / Dict[epcount_key])
			Log("Episode Runtime (avg in ms): " + str(metadata.duration))
		except: pass
		Dict.Reset()