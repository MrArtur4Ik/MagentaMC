import perlin_noise

class WorldGenerator:
	def generate(self, world): pass

class ClassicGenerator(WorldGenerator):
	def generate(self, world):
		noise = perlin_noise.PerlinNoise(20, world.seed) #Для получения океанов
		noise1 = perlin_noise.PerlinNoise(60, world.seed) #Для ландшафта на суше
		noise2 = perlin_noise.PerlinNoise(70, world.seed+1) #Для эрозии
		devide = 2400
		water_level = max(world.height//2-1, 0)
		for i in range(world.width):
			for j in range(world.depth):
				height = (noise([i/devide, j/devide])/2+0.5)**2
				if height > 0.2: #Для создания холмистой местности над уровнем моря
					h = (noise1([i/900, j/1100])/2+0.5)**6 + (noise2([i/300, j/300])/2+0.5)**1.5 * 0.05
					#height = (height+h)/2
					height *= h+1
					height = height%1
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