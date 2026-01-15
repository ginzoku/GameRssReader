import importlib.util, sys, os
print('cwd', os.getcwd())
print('exists gamer dir?', os.path.isdir('gamer'))
print('listdir:', os.listdir('gamer'))
spec = importlib.util.find_spec('gamer')
print('spec', spec)
