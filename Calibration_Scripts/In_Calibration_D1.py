from MBE_Tools import *
from numpy import remainder
from time import strftime
connection=ServerConnection("10.18.7.24","55001","xxa")
values=range(770,840,10)
#values=range(515,525,5)

# example: values=[890,892,...]
waitShutter=120
waitTime=300
waitRepeat=60
repeat=3
mat="In"
final=515
#filename=r"C:\Users\epfl\Calibrations\2013-04-08_Ga_Flux1.txt"
filename=r"\\MBESERVER\Documents\Calibrations_D1"+"\\"+strftime("%Y-%m-%d_%H-%M-%S_"+mat+".txt")

def waiting(time):
    for i in xrange(int(round(time*10))):
        if not remainder(i,100):
            print "%ds left"%(time-i/10.)
        sleep(0.1)    
if not connection.sendCommand("get this.recipesrunning") == "0":
	raise Exception("At least one recipe is running!")
try:
	connection.sendCommand("set this.recipesrunning inc")
	connection.sendCommand("Set BFM.LT.IN")  
	connection.sendCommand("Set "+mat+".PV.Rate 10")
	connection.sendCommand("Set "+mat+".OP.Rate 0")     
	for value in values:
		connection.sendCommand("Set "+mat+".PV.TSP %d"%value)
		check=True
		print "Ramping to %d"%value
		while check:
			waiting(1)
			if values[1]>values[0]:
				if connection.getValue(mat+".PV") >= value -0.1:
					check=False
			else:
				if connection.getValue(mat+".PV") <= value +0.1:
					check=False
		print "Waiting to stabilize"
		waiting(waitTime)	
		for i in range(repeat):
			connection.sendCommand("Open "+mat)
			print "Opened shutter"
			waiting(waitShutter)
			pressure=connection.sendCommand("Get BFM.P")
			background=connection.sendCommand("Get MBE.P")
			f=open(filename,"a")
			f.write("%d"%value+"\t"+pressure+"\t"+background+"\n")
			f.close()
			print "Pressure: "+pressure+ " (stored to file)"
			connection.sendCommand("Close "+mat)
			print "Closed shutter"
			waiting(waitRepeat)
	connection.sendCommand("Set "+mat+".PV.TSP %d"%final)
	connection.sendCommand("Set BFM.LT.OUT") 
	connection.sendCommand("set this.recipesrunning dec")
	connection.close()
	print "Done"
except Exception as e:
	print e
	connection.sendCommand("set this.recipesrunning dec")
	connection.close()
except KeyboardInterrupt as e:
	print e
	connection.sendCommand("set this.recipesrunning dec")
	connection.close()

