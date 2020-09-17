import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import os, random, json, asyncio
from os import path
from dotenv import load_dotenv

from modules.core.client import Client
from modules.core.database import Database
from modules.config.user import User
from modules.anime.safebooru import Safebooru
from modules.anime.anilist import Anilist
from modules.anime.anilist2 import Anilist2
from modules.anime.mal import Mal
from modules.anime.vndb import Vndb
from modules.config.config import Config

class Anime(commands.Cog):

	load_dotenv()

	al_json_path = os.getenv("OS_PATH")+"/modules/anime/config/alID.json"
	al_json = json.load(open(al_json_path, 'r'))

	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def safebooru(self, ctx, tags): #looks up images on safebooru

		channel = ctx.message.channel

		safebooruSearch = Safebooru.booruSearch(tags)

		safebooruImageURL = safebooruSearch[0]
		safebooruPageURL = safebooruSearch[1]
		safebooruTagsTogether = safebooruSearch[2]

		embed = discord.Embed(
			title = tags,
			description = 'Here\'s the picture you were looking for:',
			color = discord.Color.green(),
			url = safebooruPageURL
		)

		embed.set_image(url=safebooruImageURL)
		embed.set_footer(text=safebooruTagsTogether)

		await channel.send(embed=embed)

	@commands.group(pass_context=True)
	async def al(self, ctx):
		# anilist command group
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid anilist command passed...')

	@al.command(pass_context=True)
	async def help(self, ctx):
		await ctx.trigger_typing()
		embed = discord.Embed(
			title = 'Available commands',
			description = '',
			color = discord.Color.blue(),
		)
		embed.add_field(name='al animelist enable', value='Requires admin. Enable anilist anime updates messages on this channel. The same can be done for \'mangalist\'. Replace \'enable\' with \'disable\' to stop message updates.', inline=False)
		embed.add_field(name='al search \<show\>', value='search for anime in anilist', inline=False)
		embed.add_field(name='al manga \<manga\>', value='search for manga in anilist', inline=False)
		embed.add_field(name='al user set \<username\>', value='connect anilist account to discord account', inline=False)
		embed.add_field(name='al user remove', value='disconnect anilist account from discord account', inline=False)
		embed.add_field(name='+more', value='I\'m too lazy to do describe all of them. There\'s safebooru, al char, al user profile', inline=False)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	async def search(self, ctx):
		await ctx.trigger_typing()
		show = str(ctx.message.content)[(len(ctx.prefix) + len('al search ')):]
		# retrieve json file
		anilistResults = Anilist.aniSearch(show)
		showID = anilistResults["data"]["Media"]["id"]

		# parse out website styling
		desc = shorten(str(anilistResults['data']['Media']['description']))

		# make genre list look nice
		gees = str(anilistResults['data']['Media']['genres'])
		gees = gees.replace('\'', '')
		gees = gees.replace('[', '')
		gees = gees.replace(']', '')

		# embed text to output
		embed = discord.Embed(
			title = str(anilistResults['data']['Media']['title']['romaji']),
			description = desc,
			color = discord.Color.blue(),
			url = str(anilistResults['data']['Media']['siteUrl'])
		)

		embed.set_footer(text=gees)

		# images, check if valid before displaying
		if 'None' != str(anilistResults['data']['Media']['bannerImage']):
			embed.set_image(url=str(anilistResults['data']['Media']['bannerImage']))

		if 'None' != str(anilistResults['data']['Media']['coverImage']['large']):
			embed.set_thumbnail(url=str(anilistResults['data']['Media']['coverImage']['large']))

		# studio name and link to their AniList page
		try:
			embed.set_author(name=str(anilistResults['data']['Media']['studios']['nodes'][0]['name']), url=str(anilistResults['data']['Media']['studios']['nodes'][0]['siteUrl']))
		except IndexError:
			print('empty studio name or URL\n')

		# if show is airing, cancelled, finished, or not released
		status = anilistResults['data']['Media']['status']

		if 'NOT_YET_RELEASED' not in status:
			embed.add_field(name='Score', value=str(anilistResults['data']['Media']['meanScore']) + '%', inline=True)
			embed.add_field(name='Popularity', value=str(anilistResults['data']['Media']['popularity']) + ' users', inline=True)
			if 'RELEASING' not in status:
				embed.add_field(name='Episodes', value=str(anilistResults['data']['Media']['episodes']), inline=False)

				# make sure season is valid
				if str(anilistResults['data']['Media']['seasonYear']) != 'None' and str(anilistResults['data']['Media']['season']) != 'None':
					embed.add_field(name='Season', value=str(anilistResults['data']['Media']['seasonYear']) + ' ' + str(anilistResults['data']['Media']['season']).title(), inline=True)

				# find difference in year month and days of show's air time
				try:
					air = True
					years = abs(anilistResults['data']['Media']['endDate']['year'] - anilistResults['data']['Media']['startDate']['year'])
					months = abs(anilistResults['data']['Media']['endDate']['month'] - anilistResults['data']['Media']['startDate']['month'])
					days = abs(anilistResults['data']['Media']['endDate']['day'] - anilistResults['data']['Media']['startDate']['day'])
				except TypeError:
					print('Error calculating air time')
					air = False

				# get rid of anything with zero
				if air:
					tyme = str(days) + ' days'
					if months != 0:
						tyme += ', ' + str(months) + ' months'
					if years != 0:
						tyme += ', ' + str(years) + ' years'

					embed.add_field(name='Aired', value=tyme, inline=False)

		await embedScores(ctx.guild, showID, 'animeList', 9, embed)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	async def manga(self, ctx):
		comic = str(ctx.message.content)[(len(ctx.prefix) + len('al manga ')):]
		# retrieve json file
		anilistResults = Anilist.aniSearchManga(comic)
		mangaID = anilistResults["data"]["Media"]["id"]

		# parse out website styling
		desc = shorten(str(anilistResults['data']['Media']['description']))

		# make genre list look nice
		gees = str(anilistResults['data']['Media']['genres'])
		gees = gees.replace('\'', '')
		gees = gees.replace('[', '')
		gees = gees.replace(']', '')

		# embed text to output
		embed = discord.Embed(
			title = str(anilistResults['data']['Media']['title']['romaji']),
			description = desc,
			color = discord.Color.blue(),
			url = str(anilistResults['data']['Media']['siteUrl'])
		)

		embed.set_footer(text=gees)
		embed.add_field(name = 'Format', value=str(anilistResults['data']['Media']['format']).title())

		# images, check if valid before displaying
		if 'None' != str(anilistResults['data']['Media']['bannerImage']):
			embed.set_image(url=str(anilistResults['data']['Media']['bannerImage']))

		if 'None' != str(anilistResults['data']['Media']['coverImage']['large']):
			embed.set_thumbnail(url=str(anilistResults['data']['Media']['coverImage']['large']))


		# if show is airing, cancelled, finished, or not released
		status = anilistResults['data']['Media']['status']

		if 'NOT_YET_RELEASED' not in status:
			embed.add_field(name='Score', value=str(anilistResults['data']['Media']['meanScore']) + '%', inline=True)
			embed.add_field(name='Popularity', value=str(anilistResults['data']['Media']['popularity']) + ' users', inline=True)
			if 'RELEASING' not in status:
				embed.add_field(name='Chapters', value=str(anilistResults['data']['Media']['chapters']), inline=False)
				# find difference in year month and days of show's air time
				try:
					air = True
					years = abs(anilistResults['data']['Media']['endDate']['year'] - anilistResults['data']['Media']['startDate']['year'])
					months = abs(anilistResults['data']['Media']['endDate']['month'] - anilistResults['data']['Media']['startDate']['month'])
					days = abs(anilistResults['data']['Media']['endDate']['day'] - anilistResults['data']['Media']['startDate']['day'])
				except TypeError:
					print('Error calculating air time')
					air = False

				# get rid of anything with zero
				if air:
					tyme = str(days) + ' days'
					if months != 0:
						tyme += ', ' + str(months) + ' months'
					if years != 0:
						tyme += ', ' + str(years) + ' years'

					embed.add_field(name='Released', value=tyme, inline=False)

		await embedScores(ctx.guild, mangaID, 'mangaList', 9, embed)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	async def char(self, ctx):
		c = str(ctx.message.content)[(len(ctx.prefix) + len('al char ')):]
		anilistResults = Anilist.charSearch(c)

		embed = discord.Embed(
				title = str(anilistResults['data']['Character']['name']['full']),
				color = discord.Color.blue(),
				url = str(anilistResults['data']['Character']['siteUrl'])
			)

		# make alternative names look nice
		alts = str(anilistResults['data']['Character']['name']['alternative'])
		alts = alts.replace('\'', '')
		alts = alts.replace('[', '')
		alts = alts.replace(']', '')

		image = str(anilistResults['data']['Character']['image']['large'])
		if (image != 'None'):
			embed.set_image(url=image)

		try:
			embed.set_author(name=str(anilistResults['data']['Character']['media']['nodes'][0]['title']['romaji']), url=str(anilistResults['data']['Character']['media']['nodes'][0]['siteUrl']), icon_url=str(anilistResults['data']['Character']['media']['nodes'][0]['coverImage']['medium']))
		except IndexError:
			print('Character had empty show name or url, or image')

		embed.set_footer(text=alts)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	@has_permissions(administrator=True)
	async def animelist_old(self, ctx):
		try:
			if Config.cfgRead(str(ctx.guild.id), "alAnimeChannel")==ctx.channel.id:
				Config.cfgUpdate(str(ctx.guild.id), "alAnimeChannel", 0)
				Config.cfgUpdate(str(ctx.guild.id), "alAnimeOn", False)
				await ctx.send("Disabled AniList Anime messages in this channel!")
			elif Config.cfgRead(str(ctx.guild.id), "alAnimeChannel")!=0:
				Config.cfgUpdate(str(ctx.guild.id), "alAnimeChannel", ctx.channel.id)
				Config.cfgUpdate(str(ctx.guild.id), "alAnimeOn", True)
				await ctx.send("Moved and enabled AniList Anime messages to this channel!")
			else: #this is seperate just in case, i forgot why while coding
				Config.cfgUpdate(str(ctx.guild.id), "alAnimeChannel", ctx.channel.id)
				Config.cfgUpdate(str(ctx.guild.id), "alAnimeOn", True)
				await ctx.send("Enabled AniList Anime messages in this channel!")
		except:
			await ctx.send("error! LOL!")

	@al.group(pass_context=True)
	async def animelist(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid animelist command passed...\nTry \"\>al animelist enable\" to enable anime updates on this channel or use disable.')
	
	@animelist.command(pass_context=True, name="enable")
	@has_permissions(administrator=True)
	async def animelist_enable(self, ctx):
		res = await Database.guildCollection().update_one(
			{ 'id': ctx.guild.id },
			{  '$addToSet': { 'animeMessageChannels': ctx.channel.id } },
			upsert=True
		)
		# if the update created a new document, populate it with the rest of the info
		if res.upserted_id:
			await Database.guildCollection().update_one(
				{ '_id': res.upserted_id },
				{ '$set': { 'name': ctx.guild.name, 'mangaMessageChannels': [] } }
			)

		await ctx.send("Enabled AniList Anime messages in this channel!")

		# now update all the users to use this channel. this is so individual control can be added later
		await Database.userCollection().update_many(
			{ 'discordId': {'$in': [user.id for user in ctx.guild.members]} },
			{ '$addToSet': {'animeMessageGuilds': ctx.guild.id} }
		)

	@animelist.command(pass_context=True, name="disable")
	@has_permissions(administrator=True)
	async def animelist_diable(self, ctx):
		await Database.guildCollection().update_one(
			{ 'id': ctx.guild.id },
			{  '$pullAll': { 'animeMessageChannels': [ctx.channel.id] } },
		)
		await ctx.send("Anime messages disabled for this channel!")

	@al.group(pass_context=True)
	async def mangalist(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid mangalist command passed...\nTry \"\>al mangalist enable\" to enable manga updates on this channel or use disable.')
	
	@mangalist.command(pass_context=True, name="enable")
	@has_permissions(administrator=True)
	async def mangalist_enable(self, ctx):
		res = await Database.guildCollection().update_one(
			{ 'id': ctx.guild.id },
			{  '$addToSet': { 'mangaMessageChannels': ctx.channel.id } },
			upsert=True
		)
		# if the update created a new document, populate it with the rest of the info
		if res.upserted_id:
			await Database.guildCollection().update_one(
				{ '_id': res.upserted_id },
				{ '$set': { 'name': ctx.guild.name, 'animeMessageChannels': [] } }
			)

		await ctx.send("Enabled AniList Manga messages in this channel!")

		# now update all the users to use this channel. this is so individual control can be added later
		await Database.userCollection().update_many(
			{ 'discordId': {'$in': [user.id for user in ctx.guild.members]} },
			{ '$addToSet': {'mangaMessageGuilds': ctx.guild.id} }
		)

	@mangalist.command(pass_context=True, name="disable")
	@has_permissions(administrator=True)
	async def mangalist_disable(self, ctx):
		await Database.guildCollection().update_one(
			{ 'id': ctx.guild.id },
			{  '$pullAll': { 'mangaMessageChannels': [ctx.channel.id] } },
		)
		await ctx.send("Manga messages disabled for this channel!")

	@al.command(pass_context=True)
	@has_permissions(administrator=True)
	async def mangalist_old(self, ctx):
		try:
			if Config.cfgRead(str(ctx.guild.id), "alMangaChannel")==ctx.channel.id:
				Config.cfgUpdate(str(ctx.guild.id), "alMangaChannel", 0)
				Config.cfgUpdate(str(ctx.guild.id), "alMangaOn", False)
				await ctx.send("Disabled AniList Manga messages in this channel!")
			elif Config.cfgRead(str(ctx.guild.id), "alMangaChannel")!=0:
				Config.cfgUpdate(str(ctx.guild.id), "alMangaChannel", ctx.channel.id)
				Config.cfgUpdate(str(ctx.guild.id), "alMangaOn", True)
				await ctx.send("Moved and enabled AniList Manga messages to this channel!")
			else: #this is seperate just in case, i forgot why while coding
				Config.cfgUpdate(str(ctx.guild.id), "alMangaChannel", ctx.channel.id)
				Config.cfgUpdate(str(ctx.guild.id), "alMangaOn", True)
				await ctx.send("Enabled AniList Manga messages in this channel!")
		except:
			await ctx.send("error! LOL!")

	@al.group(pass_context=True)
	async def user(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid Anilist user command passed...')

	# al user
	@user.command()
	async def set_old(self, ctx, user):
		#try:
		User.userUpdate(str(ctx.message.author.id), "alName", user)
		try:
			userID = Anilist.userSearch(user)["data"]["User"]["id"]
			User.userUpdate(str(ctx.message.author.id), "alID", userID)
			await ctx.send("Updated AL username!")
			with open(os.getcwd()+"/modules/anime/config/alID.json", 'r') as al_json:
				json_data = json.load(al_json)
				json_data[str(ctx.message.author.id)] = str(userID)
			with open(os.getcwd()+"/modules/anime/config/alID.json", 'w') as al_json:
				al_json.write(json.dumps(json_data))
		except Exception as e:
			print(e)
			await ctx.send("Failed to update AL username!")

	@user.command(name="set")
	async def set_(self, ctx, user):
		await ctx.trigger_typing()
		search = await Anilist2.userSearch(self.bot.get_cog('Session').session, user)
		if search.get('errors'):
			notFound = False
			for error in search['errors']:
				if error['message'] == 'Not Found.':
					notFound =  True
					break
			if notFound:
				await ctx.send('Sorry, could not find that user')
			else:
				await ctx.send('Error!')
		else:
			def check(reaction, user):
				return user == ctx.message.author and (str(reaction.emoji) == '✅' or str(reaction.emoji) == '❌')
			await ctx.send('Is this you?')	
			embed = discord.Embed(
				title = search['data']['User']['name'],
				description = search['data']['User']['about'] if search['data']['User']['about'] else '',
				color = discord.Color.blue(),
				url = 'http://anilist.co/user/'+str(search['data']['User']['id'])
			)
			embed.set_thumbnail(url=search['data']['User']['avatar']['large'])
			msg = await ctx.send(embed=embed)
			await msg.add_reaction('✅')
			await msg.add_reaction('❌')

			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=5.0, check=check)
			except asyncio.TimeoutError:
				await ctx.send('User not updated')
			else:
				if str(reaction.emoji) == '✅':
					await ctx.trigger_typing()
					lists = generateLists(search)
					await Database.userCollection().update_one(
						{'discordId': ctx.message.author.id}, 
						{'$set': { 
							'anilistId': search['data']['User']['id'],
							'anilistName': search['data']['User']['name'],
							'animeList': lists['animeList'], 
							'mangaList': lists['mangaList'], 
							'profile': search['data']['User'],
							'animeMessageGuilds': [],
							'mangaMessageGuilds': []
							}
						},
						upsert=True
					)
					await ctx.send('Your details have been updated!')
				else:
					await ctx.send('Your details have NOT been updated!')

	@user.command()
	async def remove(self, ctx):
		res = await Database.userCollection().update_one(
			{ 'discordId': ctx.message.author.id },
			{ '$set': { 'animeMessageGuilds': [], 'mangaMessageGuilds': [] } }
		)
		if res.matched_count:
			await ctx.send('You have been removed!')
		else:
			await ctx.send('You were never registered.')

	@user.command()
	async def remove_old(self, ctx):
		user = str(ctx.message.content)[(len(ctx.prefix) + len('al user remove ')):]
		atLen = len(user)-5
		if user == "":
			try:
				User.userUpdate(str(ctx.message.author.id), "alName", None)
				User.userUpdate(str(ctx.message.author.id), "alID", 0)
				with open(os.getcwd()+"/modules/anime/config/alID.json", 'r') as al_json:
					json_data = json.load(al_json)
					json_data[str(ctx.message.author.id)] = 0
				with open(os.getcwd()+"/modules/anime/config/alID.json", 'w') as al_json:
					al_json.write(json.dumps(json_data))
				await ctx.send("Removed AL account from your profile!")
			except:
				user = None
				await ctx.send("Failed to remove AL account from your profile!")
		try:
			if ctx.message.author.guild_permissions.administrator:
				if user.startswith("<@!"):
					userLen = len(user)-1
					atUser = user[3:userLen]
					try:
						User.userUpdate(str(atUser), "alName", None)
						User.userUpdate(str(atUser), "alID", 0)
						with open(os.getcwd()+"/modules/anime/config/alID.json", 'r') as al_json:
							json_data = json.load(al_json)
							json_data[str(atUser)] = 0
						with open(os.getcwd()+"/modules/anime/config/alID.json", 'w') as al_json:
							al_json.write(json.dumps(json_data))
						await ctx.send("Removed AL account from "+user+".")
					except:
						await ctx.send("Error removing AL account from "+user+".")
				# re.findall(".+#[0-9]{4}", txt)
				elif user[atLen]=="#":
					for users in self.bot.users:
						usersSearch = users.name+"#"+users.discriminator
						if usersSearch == user:
							try:
								with open(os.getcwd()+"/modules/anime/config/alID.json", 'r') as al_json:
									json_data = json.load(al_json)
									json_data[str(users.id)] = 0
								with open(os.getcwd()+"/modules/anime/config/alID.json", 'w') as al_json:
									al_json.write(json.dumps(json_data))
								User.userUpdate(str(users.id), "alName", None)
								User.userUpdate(str(users.id), "alID", 0)
								await ctx.send("Removed AL account from "+user+".")
							except:
								await ctx.send("Error removing AL account from "+user+".")
			else:
				await ctx.send("You do not have permissions to remove AL from others!")
		except:
			pass

	# al user
	@user.command()
	async def profile(self, ctx):
		user = str(ctx.message.content)[(len(ctx.prefix) + len('al user profile ')):]
		# when the message contents are something like "@Sigurd#6070", converts format into "<@!user_id>"

		atLen = len(user)-5
		if user == "":
			try:
				user = User.userRead(str(ctx.message.author.id), "alName")
			except:
				user = None
		elif user.startswith("<@!"):
			userLen = len(user)-1
			atUser = user[3:userLen]
			try:
				user = User.userRead(str(atUser), "alName")
			except:
				user = None
		# re.findall(".+#[0-9]{4}", txt)
		elif user[atLen]=="#":
			for users in self.bot.users:
				usersSearch = users.name+"#"+users.discriminator
				if usersSearch == user:
					try:
						user = User.userRead(str(users.id), "alName")
					except:
						return None

		try:
			anilistResults = Anilist.userSearch(user)["data"]["User"]
		except:
			print(user)
			if user == None:
				await ctx.send("Error! Make sure you've set your profile using ``>al user set``!")
			else:
				await ctx.send("Error! Make sure you're spelling everything correctly!")
		try:
			color = colorConversion(anilistResults["options"]["profileColor"])
		except:
			color = discord.Color.teal()
		userUrl = anilistResults["siteUrl"]

		embed = discord.Embed(
			title = anilistResults["name"],
			color = color,
			url = userUrl
		)

		try:
			animeGenres = anilistResults["statistics"]["anime"]["genres"][0]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][1]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][2]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][3]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][4]["genre"]
		except:
			animeGenres = "None"

		# core user fields


		if anilistResults["bannerImage"]!=None:
			try:
				embed.set_image(url=anilistResults["bannerImage"])
			except:
				pass
		try:
			embed.set_thumbnail(url=anilistResults["avatar"]["large"])
		except:
			pass
		try:
			embed.add_field(name="About:", value=str(anilistResults["about"]), inline=False)
		except:
			pass
		try:
			embed.set_footer(text="Last update: "+str(anilistResults["updatedAt"]))
		except:
			pass

		# anime fields
		try:
			embed.add_field(name="Anime count:", value=str(anilistResults["statistics"]["anime"]["count"]), inline=True)
		except:
			pass
		try:
			embed.add_field(name="Mean anime score:", value=str(anilistResults["statistics"]["anime"]["meanScore"])+"/100.00", inline=True)
		except:
			pass
		try:
			embed.add_field(name="Top anime genres:", value=animeGenres, inline=False)
		except:
			pass
		try:
			await ctx.send(embed=embed)
		except Exception as e:
			print(e)
			print(anilistResults["bannerImage"])
			print(anilistResults["avatar"]["large"])
			print(anilistResults["siteUrl"])
			await ctx.send(e)

	@commands.group(pass_context=True)
	async def vn(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid vndb command passed...')

	@vn.command(pass_context=True)
	async def get(self, ctx):
		# name of vn
		arg = str(ctx.message.content)[(len(ctx.prefix) + len('vn get ')):]
		try:
			# grab info from database
			vn = Vndb()
			r = vn.vn(arg.strip())
			r = r['items'][0]

			# assign variables
			title = r['title']
			link = 'https://vndb.org/v' + str(r['id'])

			try:
				desc = shorten(r['description'])
			except:
				desc = 'Empty Description'
			# ----
			try:
				score = str(r['rating'])
			except:
				score = 'Unknown'
			# ----
			try:
				votes = str(r['votecount'])
			except:
				votes = 'Unknown'
			# ----
			try:
				popularity = str(r['popularity'])
			except:
				popularity = 'Unknown'
			# ----
			try:
				released = r['released']
			except:
				released = 'Unknown'
			# ----
			try:
				length = {
					1 : 'Very Short (< 2 hours)',
					2 : 'Short (2 - 10 hours)',
					3 : 'Medium (10 - 30 hours)',
					4 : 'Long (30 - 50 hours)',
					5 : 'Very Long (> 50 hours)'
				}[r['length']]
			except:
				length = 'Unknown'
			# ----
			try:
				image = r['image']
			except:
				image = 'https://i.kym-cdn.com/photos/images/original/000/290/992/0aa.jpg'
			# ----
			try:
				screens = r['screens']
			except:
				screens = []
			# ----
			try:
				langs = str(r['languages']).replace('[', '').replace(']', '').replace('\'','')
			except:
				langs = 'Unknown'
			# ----
			try:
				platforms = str(r['platforms']).replace('[', '').replace(']', '').replace('\'','')
			except:
				platforms = 'Unknown'
			# NSFW images disabled by default
			nsfw = False

			# display info on discord
			embed = discord.Embed(
					title = title,
					description = desc,
					color = discord.Color.purple(),
					url = link
				)
			try:
				embed.set_author(name='vndb')
			except:
				pass

			# adding fields to embed
			if score != 'Unknown':
				embed.add_field(name='Score', value=score, inline=True)
			if votes != 'Unknown':
				embed.add_field(name='Votes', value=votes, inline=True)
			if popularity != 'Unknown':
				embed.add_field(name='Popularity', value=popularity, inline=True)
			if released != 'Unknown':
				embed.add_field(name='Released', value=released, inline=True)
			if length != 'Unknown':
				embed.add_field(name='Time To Complete', value=length, inline=True)
			if langs != 'Unknown':
				embed.add_field(name='Languages', value=langs, inline=True)
			if platforms != 'Unknown':
				embed.add_field(name='Platforms', value=platforms, inline=True)

			embed.set_footer(text='NSFW: {0}'.format({False : 'off', True : 'on'}[nsfw]))

			embed.set_thumbnail(url=image)

			# Filter out porn
			risky = []
			for pic in screens:
				if pic['nsfw']:
					risky.append(pic)

			for f in risky:
				screens.remove(f)

			# Post image
			if len(screens) >= 1:
				embed.set_image(url=random.choice(screens)['image'])

			await ctx.send(embed=embed)
		except Exception as e:
			print(e)
			await ctx.send('VN not found (title usually has to be exact)')
	
	@vn.command(pass_context=True)
	async def quote(self, ctx):
		q = Vndb()
		quote = q.quote()

		embed = discord.Embed(
					title = quote['quote'],
					color = discord.Color.purple()
				)
		
		embed.set_author(name=quote['title'], url='https://vndb.org/v' + str(quote['id']), icon_url=quote['cover'])

		await ctx.send(embed=embed)

def shorten(desc):
	# italic
	desc = desc.replace('<i>', '*')
	desc = desc.replace('</i>', '*')
	# bold
	desc = desc.replace('<b>', '**')
	desc = desc.replace('</b>', '**')
	# remove br
	desc = desc.replace('<br>', '')

	# keep '...' in
	desc = desc.replace('...', '><.')

	# limit description to three sentences
	sentences = findSentences(desc)
	if len(sentences) > 3:
		desc = desc[:sentences[2] + 1]

	# re-insert '...'
	desc = desc.replace('><', '..')

	return desc

def findSentences(s):
	return [i for i, letter in enumerate(s) if letter == '.' or letter == '?' or letter == '!']

def colorConversion(arg):
	colors = {
		"blue": discord.Color.blue(),
		"purple": discord.Color.purple(),
		"pink": discord.Color.magenta(),
		"orange": discord.Color.orange(),
		"red": discord.Color.red(),
		"green": discord.Color.green(),
		"gray": discord.Color.light_grey()
	}
	return colors.get(arg, discord.Color.teal())

def statusConversion(arg):
	colors = {
		"CURRENT": "W",
		"PLANNING": "P",
		"COMPLETED": "C",
		"DROPPED": "D",
		"PAUSED": "H",
		"REPEATING": "R"
	}
	return colors.get(arg, "X")

def scoreFormat(user):
	fmt = user['profile']['mediaListOptions']['scoreFormat']
	if fmt == 'POINT_100':
		return '100'
	elif fmt == 'POINT_10_DECIMAL' or fmt == 'POINT_10':
		return '10'
	elif fmt == 'POINT_5':
		return '5'
	else:
		return '3'

async def embedScores(guild, showID, listType, maxDisplay, embed):
		# get all users in db that are in this guild and have the show on their list
		userIdsInGuild = [u.id for u in guild.members]
		users = [d async for d in Database.userCollection().find(
			{
				'discordId': { '$in': userIdsInGuild },
				listType+'.'+str(showID): { '$exists': True }
			},
			{
				'anilistName': 1,
				listType+'.'+str(showID): 1,
				'profile.mediaListOptions': 1
			}
			)
		]

		usrLen = len(users)
		for i in range(0, min(usrLen, maxDisplay-1)):
			userScoreEmbeder(users[i], showID, 'animeList', embed)

		# either load last or say there are '+XX others'
		if usrLen == maxDisplay:
			userScoreEmbeder(users[maxDisplay], showID, 'animeList', embed)
		elif usrLen > maxDisplay:
			embed.add_field(name='+'+str(usrLen-maxDisplay+1)+' others', value="...", inline=True)

def userScoreEmbeder(user, showID, listType, embed):
	userInfo = user[listType][str(showID)]
	status = statusConversion(userInfo['status'])
	score = userInfo['score']
	scoreFmt = scoreFormat(user)
	if not score or score == 0:
		embed.add_field(name=user['anilistName'], value="No Score ("+status+")", inline=True)
	else:
		embed.add_field(name=user['anilistName'], value=str(score)+"/"+scoreFmt+" ("+status+")", inline=True)

def generateLists(user):
	lists = { 'animeList': {}, 'mangaList': {} }

	for lst in user['data']['animeList']['lists']:
		for entry in lst['entries']:
			lists['animeList'][str(entry['mediaId'])] = Database.formListEntryFromAnilistEntry(entry, anime=True)

	for lst in user['data']['mangaList']['lists']:
		for entry in lst['entries']:
			lists['mangaList'][str(entry['mediaId'])] = Database.formListEntryFromAnilistEntry(entry, anime=False)

	return lists