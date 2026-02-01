import perlin_noise

class WorldGenerator:
	def generate(self, world): pass

class ClassicGenerator(WorldGenerator):
	def generate(self, world):
		
		noise = perlin_noise.PerlinNoise(20, world.seed) #Основной шум для получения океанов
		noise1 = perlin_noise.PerlinNoise(60, world.seed) #Для ландшафта на суше
		noise2 = perlin_noise.PerlinNoise(70, world.seed+1) #Для эрозии

		noise_scale = (2400, 2400)
		noise1_scale = (900, 1100)
		noise2_scale = (300, 300)

		water_level = max(world.height//2-1, 0)
		for i in range(world.width):
			for j in range(world.depth):
				#Создаём основную карту высот из первостепенного шума
				height = (noise([i/noise_scale[0], j/noise_scale[1]])/2+0.5)**2

				#Создаём эрозию
				#if height > 0.2:
				h = (noise1([i/noise1_scale[0], j/noise1_scale[1]])/2+0.5)**6 + \
					(noise2([i/noise2_scale[0], j/noise2_scale[1]])/2+0.5)**1.5 * 0.05
				#height = (height+h)/2
				height *= h+1
				height = height%1


				#Получаем высоту в блоках
				height = int(height*80+water_level-15)
				#Dirt
				for h in range(height):
					world.set_block(i, h, j, 3)
				#Grass or Sand
				if water_level-3 <= height < water_level+3: #Sand
					world.set_block(i, height-1, j, 12)
				elif height < water_level-3:
					world.set_block(i, height-1, j, 13) #Gravel
				else: #Grass
					world.set_block(i, height-1, j, 2)
				if height <= water_level:
					for h in range(water_level+1-height):
						world.set_block(i, water_level-h, j, 9)

class FlatGenerator(WorldGenerator):
	def generate(self, world):
		grass_level = world.height//2
		for i in range(world.width):
			for j in range(world.depth):
				for h in range(grass_level):
					world.set_block(i, h, j, 3, False)
				world.set_block(i, grass_level, j, 2, False)