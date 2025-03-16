import pygame
from numpy import *
import random
from collections import deque

class Faction:
	def __init__(self, name: str = None, innerColor: list[int, int, int] = None, outerColor: list[int, int, int] = None):
		self.name = name
		self.innerColor = innerColor
		self.outerColor = outerColor
		self.bases = []
		self.soldiers = []
		self.tasks = []
	
	def GetUnownedAdjacentBases(self, gameInstance: "Game"):
		bases = []
		for base in self.bases:
			if base.north is not None and base.north.faction != self and base.north not in bases:
				bases.append(base.north)
			if base.east is not None and base.east.faction != self and base.east not in bases:
				bases.append(base.east)
			if base.south is not None and base.south.faction != self and base.south not in bases:
				bases.append(base.south)
			if base.west is not None and base.west.faction != self and base.west not in bases:
				bases.append(base.west)
		return bases
	
	def AssignClaimTask(self, soldier: "Soldier", base: "Base", gameInstance: "Game"):
		task = Task.CaptureBase(soldier, base, gameInstance.gameWorld.bases)
		soldier.currentTask = task
		self.tasks.append(task)
	
	def CreateSoldier(self, gameInstance: "Game"):
		i = random.randrange(0, len(self.bases))

		soldier = Soldier(self, self.bases[i], gameInstance)
		self.soldiers.append(soldier)
	
	def Update(self, gameInstance: "Game"):
		unownedAdjacentBases = self.GetUnownedAdjacentBases(gameInstance)
		availableSoldiers = self.GetAvailableSoldiers()
		basesBeingCaptured = self.GetAllCaptureTaskBases()
		unownedAdjacentBases = Utility.RemoveAllBFromA(unownedAdjacentBases, basesBeingCaptured)

		if len(availableSoldiers) > 0 and len(unownedAdjacentBases) > 0:
			soldier = availableSoldiers[random.randrange(0, len(availableSoldiers))]
			base = unownedAdjacentBases[random.randrange(0, len(unownedAdjacentBases))]
			self.AssignClaimTask(soldier, base, gameInstance)

		for soldier in self.soldiers:
			soldier.Update(gameInstance)
	
	def GetAvailableSoldiers(self):
		soldiers = []
		for soldier in self.soldiers:
			if not soldier.HasTask():
				soldiers.append(soldier)
		return soldiers
	
	def GetAllCaptureTaskBases(self):
		bases = []

		for task in self.tasks:
			if task.type == Task.CAPTURE:
				if task.base in bases:
					raise Exception(f"Found a duplicate capture task when logging all capture tasks for faction: {self.name}.")
				else:
					bases.append(task.base)
		
		return bases



class Base:
	outerRadius = 20
	innerRadius = 15
	collisionSize = 10

	def __init__(self, faction: Faction, index: list[int, int], gameInstance: "Game"):
		self.transform = Transform()
		self.index = index
		self.faction = faction
		self.north = None
		self.south = None
		self.east = None
		self.west = None
	
	def GetCollisionRect(self):
		return pygame.Rect(self.transform.pos[0] - self.collisionSize//2, self.transform.pos[1] - self.collisionSize//2, self.collisionSize, self.collisionSize)
	
	def AssignToFaction(self, faction: Faction):
		self.faction.bases.remove(self)
		self.faction = faction
		faction.bases.append(self)


class GameWorld:
	def __init__(self):
		self.bases = []
		self.w = None
		self.h = None
	
	def isValidIndex(self, x: int, y: int):
		if x < 0 or x >= self.w or y < 0 or y >= self.h:
			return False
		else:
			return True
	
	def GetBase(self, x: int, y: int) -> "Base":
		if not self.isValidIndex(x, y):
			return None
		else:
			return self.bases[self.w*y+x]
	
	# direction refers to direction to baseB from baseA
	# baseA -- baseB would be an "east" connection
	# consider moving to WorldGenerator
	def ConnectBases(self, baseA: Base, baseB: Base, direction: str):
		if direction == "north":
			baseA.north = baseB
			baseB.south = baseA
		elif direction == "east":
			baseA.east = baseB
			baseB.west = baseA
		elif direction == "south":
			baseA.south = baseB
			baseB.north = baseA
		elif direction == "west":
			baseA.west = baseB
			baseB.east = baseA


class Task:
	CAPTURE = 10

	def __init__(self):
		self.type = None
		self.base = None
		self.baseRoute = deque()

		self.faction = None
		self.soldier = None

		self.destroyFlag = False
	
	def CaptureBase(soldier: "Soldier", base: "Base", gameInstance: "Game"):
		task = Task()
		task.faction = soldier.faction
		task.soldier = soldier
		task.type = Task.CAPTURE
		task.base = base
		task.baseRoute = Utility.GetBasePath(soldier.currentBase, base, gameInstance)

		return task

	def SetDestroy(self, gameInstance: "Game"):
		self.destroyFlag = True
		gameInstance.taskDestroyQueue.append(self)
	
	def GetBase(self):
		return self.base
	
	def HasNextBase(self):
		return len(self.baseRoute) > 0
	
	def __del__(self):
		pass


class Transform:
	def __init__(self):
		self.pos = [0.0, 0.0]
		self.scale = [1.0, 1.0]

	def anchor(self, parent: "Transform"):
		t = Transform()

		try:
			t.pos = [self.pos[0] + parent.pos[0], self.pos[1] + parent.pos[1]]
			t.scale = [self.scale[0] * parent.scale[0], self.scale[1] * parent.scale[1]]
		except TypeError:
			print(f"self {self}, parent {parent}")
			exit()

		return t


class Soldier:
	outerSize = 20
	innerSize = 14
	collisionSize = 10
	moveSpeed = 2

	def __init__(self, faction: Faction, currentBase: Base, gameInstance: "Game"):
		self.faction = faction
		self.transform = Transform()
		self.currentBase = currentBase
		self.nextBase = None
		self.currentTask = None
		self.velocity = [0.0, 0.0]
	
	def Update(self, gameInstance: "Game"):
		if self.IsStationedAtBase():
			self.SetPositionToCurrentBase()
			if self.HasTask():
				if self.currentTask.HasNextBase():
					self.SetTravelToNextTaskBase()
				else:
					self.currentBase.AssignToFaction(self.faction)
					self.currentTask.SetDestroy(gameInstance)
		else:
			self.UpdatePositionToVelocity()
			if self.IsCollidingWithNextBase2():
				self.SetToTargetBase()
	
	def GetCollisionRect(self):
		return pygame.Rect(self.transform.pos[0] - self.collisionSize//2, self.transform.pos[1] - self.collisionSize//2, self.collisionSize, self.collisionSize)

	def HasTask(self):
		return self.currentTask is not None
	
	def IsStationedAtBase(self):
		return self.currentBase is not None
	
	def IsCollidingWithNextBase(self):
		return self.nextBase.collisionBox in self.collisionBox.collisions
	
	def IsCollidingWithNextBase2(self):
		return self.GetCollisionRect().colliderect(self.nextBase.GetCollisionRect())
	
	def SetTravelToNextTaskBase(self):
		base = self.currentTask.baseRoute.popleft()
		self.currentBase = None
		self.nextBase = base
		distanceX = base.transform.pos[0] - self.transform.pos[0]
		distanceY = base.transform.pos[1] - self.transform.pos[1]
		distance = sqrt(distanceX*distanceX + distanceY*distanceY)
		self.velocity = [distanceX/distance * Soldier.moveSpeed, distanceY/distance * Soldier.moveSpeed]

	def SetToTargetBase(self):
		self.currentBase = self.nextBase
		self.nextBase = None
		self.velocity = [0.0, 0.0]

	def SetPositionToCurrentBase(self):
		self.transform.pos = [self.currentBase.transform.pos[0], self.currentBase.transform.pos[1]]

	def UpdatePositionToVelocity(self):
		self.transform.pos = [self.transform.pos[0] + self.velocity[0], self.transform.pos[1] + self.velocity[1]]
	
	def FetchRouteToBase(self, gameWorld, destination):
		return Utility.Base_BFS(self.currentBase, destination, gameWorld.bases)


class Renderer:
	def OffsetDim(rectData: list[float, float, float, float], dim: tuple[int, int]):
		return (rectData[0] + dim[0]/2, rectData[1] + dim[1]/2, rectData[2], rectData[3])

	def RenderBase(window, dim: tuple[int, int], base: Base):
		pos = [base.transform.pos[0] + dim[0]/2, base.transform.pos[1] + dim[1]/2]
		pygame.draw.circle(window, base.faction.outerColor, pos, Base.outerRadius)
		pygame.draw.circle(window, base.faction.innerColor, pos, Base.innerRadius)

	def RenderGameWorld(window, dim: tuple[int, int], world: GameWorld):
		for i in range(0, len(world.bases), 1):
			Renderer.RenderBase(window, dim, world.bases[i])

	def RenderSoldier(window, dim: tuple[int, int], soldier: Soldier):
		pos = [soldier.transform.pos[0] + dim[0] / 2, soldier.transform.pos[1] + dim[1]/2]
		pygame.draw.rect(window, soldier.faction.outerColor, (int(pos[0] - Soldier.outerSize/2), int(pos[1] - Soldier.outerSize/2), Soldier.outerSize, Soldier.outerSize))
		pygame.draw.rect(window, soldier.faction.innerColor, (int(pos[0] - Soldier.innerSize/2), int(pos[1] - Soldier.innerSize/2), Soldier.innerSize, Soldier.innerSize))

	def RenderFactionSoldiers(gameInstance: "Game", faction: "Faction"):
		for soldier in faction.soldiers:
			Renderer.RenderSoldier(gameInstance.window, gameInstance.dim, soldier)

	def SimpleRenderBaseConnections(window, dim: tuple[int, int], world: GameWorld):
		lineThickness = 10

		for i in range(0, len(world.bases), 1):
			base = world.bases[i]
			if base.east != None:
				pygame.draw.rect(
					window, 
					(255, 255, 255), 
					(base.transform.pos[0] + dim[0]/2, base.transform.pos[1] - lineThickness/2 + dim[1]/2, GameGenerator.baseOffset, lineThickness)
				)
			if base.south != None:
				pygame.draw.rect(
					window, 
					(255, 255, 255),
					(base.transform.pos[0] - lineThickness/2 + dim[0]/2, base.transform.pos[1] + dim[1]/2, lineThickness, GameGenerator.baseOffset)
				)

	def RenderCollisionBoxes(window, gameInstance: "Game"):
		for box in gameInstance.mainCollisionIndex:
			t = box.transformRelativeOwner()
			pygame.draw.rect(window, (0, 255, 0), Renderer.OffsetDim((t.pos[0], t.pos[1], t.scale[0], t.scale[1]), gameInstance.dim), 1)

	#if connection rendering gets slow finish this function
	def SmartRenderBaseConnections(window, dim: tuple[int, int], world: GameWorld):
		for y in range(0, world.h, 1):
			startX = world.GetBase(0, y).transform.pos[0]
			endX = None
			penDragged = False
			for x in range(1, world.w, 1):
				base = world.GetBase(x, y)


class Utility:
	def GetBasePath(start: Base, end: Base, bases: list["Base"]):
		searchQueue = deque()
		searched = []
		paths = {}
		paths[start] = [start]
		searchQueue.append(start)
		for i in range(0, len(bases), 1):
			base = searchQueue.popleft()
			if base == end:
				output = deque(paths[base])
				output.popleft()
				return output
			if base.north is not None and base.north not in searched:
				paths[base.north] = paths[base] + [base.north]
				searched.append(base.north)
				searchQueue.append(base.north)
			if base.east is not None and base.east not in searched:
				paths[base.east] = paths[base] + [base.east]
				searched.append(base.east)
				searchQueue.append(base.east)
			if base.south is not None and base.south not in searched:
				paths[base.south] = paths[base] + [base.south]
				searched.append(base.south)
				searchQueue.append(base.south)
			if base.west is not None and base.west not in searched:
				paths[base.west] = paths[base] + [base.west]
				searched.append(base.west)
				searchQueue.append(base.west)
		return []

	def RemoveAllBFromA(a: list, b: list):
		return [i for i in a if i not in b]


class GameGenerator:
	baseOffset = 80
	
	def GenerateBases(world: GameWorld, dim: tuple[int, int], gameInstance: "Game", w: int, h: int):
		world.w = w
		world.h = h

		for y in range(0, h, 1):
			for x in range(0, w, 1):
				base = Base(gameInstance.nullFaction, [x, y], gameInstance)

				x2 = float(x) * GameGenerator.baseOffset - GameGenerator.baseOffset * w / 2
				y2 = float(y) * GameGenerator.baseOffset - GameGenerator.baseOffset * h / 2

				base.transform.pos = [x2, y2]
				gameInstance.nullFaction.bases.append(base)
				world.bases.append(base)
	
	def GenerateGridConnections(world: GameWorld):
		for y in range(0, world.h, 1):
			for x in range(0, world.w, 1):
				base = world.GetBase(x, y)
				base.north = world.GetBase(x, y-1)
				base.east = world.GetBase(x+1, y)
				base.south = world.GetBase(x, y+1)
				base.west = world.GetBase(x-1, y)


class Deallocator:
	def DestroyMarkedTasks(gameInstance: "Game"):
		while len(gameInstance.taskDestroyQueue) > 0:
			task = gameInstance.taskDestroyQueue.popleft()
			Deallocator.DestroyTask(task)
	
	# intentionally not in Task class to prevent from calling
	def DestroyTask(task: "Task"):
		if task.soldier == None or task.faction == None:
			raise TypeError(f"Task {task} could not be deallocated. Needs existing soldier and faction.")
		task.soldier.currentTask = None
		task.faction.tasks.remove(task)


class Game:
	def __init__(self):
		self.window = None
		self.running = True
		self.dim = (1600, 900)

		self.gameTime = 0

		self.soldiers = []

		self.taskDestroyQueue = deque()

		self.nullFaction = None
		self.elvesFaction = None
		self.dwarvesFaction = None

		self.gameWorld = None

	def Start(self):
		self.nullFaction = Faction("Unclaimed", [255, 255, 255], [150, 150, 150])
		self.elvesFaction = Faction("Elves", [130, 80, 30], [25, 130, 40])
		self.dwarvesFaction = Faction("Dwarves", [120, 20, 20], [50, 50, 50])

		self.gameWorld = GameWorld()

		GameGenerator.GenerateBases(self.gameWorld, self.dim, self, 10, 10)
		GameGenerator.GenerateGridConnections(self.gameWorld)

		self.gameWorld.GetBase(0,9).AssignToFaction(self.elvesFaction)
		self.gameWorld.GetBase(9,9).AssignToFaction(self.dwarvesFaction)

		for i in range(0, 10, 1):
			self.elvesFaction.CreateSoldier(self)
		
		#self.elvesFaction.AssignClaimTask(self.elfSoldier, self.gameWorld.GetBase(7, 4), self)

	def Input(self):
		for e in pygame.event.get():
			if e.type == pygame.QUIT:
				self.running = False

	def Update(self):
		self.elvesFaction.Update(self)
		Deallocator.DestroyMarkedTasks(self)


	def Render(self):
		self.window.fill((0, 0, 0))
		
		Renderer.SimpleRenderBaseConnections(self.window, self.dim, self.gameWorld)
		Renderer.RenderGameWorld(self.window, self.dim, self.gameWorld)

		Renderer.RenderFactionSoldiers(self, self.elvesFaction)

		#Renderer.RenderCollisionBoxes(self.window, self)

		pygame.display.flip()

	def main(self):
		pygame.init()

		self.window = pygame.display.set_mode(self.dim)

		tps = 60.0
		ns = 1000.0 / tps
		actualTPS = 0

		delta = 0.0

		lastTime = pygame.time.get_ticks()

		fps = 30.0
		frameNS = 1000.0 / fps
		actualFPS = 0

		lastFrame = pygame.time.get_ticks()

		timer = pygame.time.get_ticks()

		reportRefreshRate = False

		self.Start()

		while self.running:
			self.Input()

			nowTime = pygame.time.get_ticks()
			delta += float(nowTime-lastTime) / ns
			lastTime = nowTime

			while not (delta < 1):
				self.Update()
				self.gameTime += 1
				actualTPS += 1
				delta -= 1.0
			
			nowFrame = pygame.time.get_ticks()
			if float(nowFrame-lastFrame) > frameNS:
				lastFrame = nowFrame
				self.Render()
				actualFPS += 1
			
			nowTimer = pygame.time.get_ticks()
			if nowTimer - timer > 1000:
				timer = nowTimer
				if reportRefreshRate:
					print(f"TPS: {actualTPS}\nFPS: {actualFPS}")
				actualTPS = 0
				actualFPS = 0

		pygame.quit()


if __name__ == "__main__":
	g = Game()
	g.main()
