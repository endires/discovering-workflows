import sys
import sqlite3
import csv
import argparse
from collections import Counter
from collections import OrderedDict 
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import euclidean_distances
from operator import itemgetter

#Simple shell-workflow-autocomplete program:Finished Exact match
#Given an initial command (e.g., git, ps, du, etc.) provide a ranked autocomple^te functionality.
# More concretely, write a program called shell-workflow-autocomplete that takes as parameter one command (potentially with parameters) and returns a ranked list of pipelines.
#
#Feel free to restrict the space of programs you consider for this autocomplete problem (e.g., only get pipelines of a certain size).
#The easiest formulation for this problem is to start with just conditioning on the first command and returning a list which is ranked by frequency of occurrence.

#https://staff.fnwi.uva.nl/m.derijke/wp-content/papercite-data/pdf/cai-survey-2016.pdf

#-https://www.sciencedirect.com/science/article/pii/S1389128605003646?via%3Dihub#bib8 -in classical ir


#Example:
#./shell-workflow-autocomplete git commit
#Output in CSV:
#Full Pipeline, Frequency
#git log | wc -l | 2343
#git log | tail -n 17 | 1234
#
#If you restrict this to Pipelines of Size 2, this should only be 1 simple SQL Query. Otherwise its a bit longer SQL Query.


#1. alias_id  command_id command.name 
#	- where : command name like and arguments like 
#2. alias_id command_id operator command.name
#	- where operator/name/args like And command = in position 
#3. alias_id, command_id, name 
# - where argument = x in position = x and command_id in 1&2 

firstquery = "SELECT  command.alias_id , command.name, command.arguments from command join alias on command.alias_id =  alias.alias_id WHERE command.name  {}  And command.arguments LIKE \"{}\" And command.position = 0 And alias.num_commands =  \"{}\" And command.num_arguments =  \"{}\"  Order By command.alias_id;"

restquery = "SELECT  command.alias_id, command.command_id, command.operator, command.name, command.arguments from command join alias on command.alias_id =  alias.alias_id WHERE command.operator = \"{}\"  And command.name  {}  And command.arguments LIKE \"{}\" And command.position = \"{}\" And command.num_arguments = \"{}\" And alias.alias_id IN {}  Order By command.alias_id;"

argquery = " SELECT command.alias_id  from argument join command on command.command_id =  argument.command_id WHERE argument.name  {}  And argument.position = \"{}\"  And argument.command_id = {} Order By command.alias_id;"

# Select the alias and the command from the chosen ones till now where value of the position of a given argument is = to the arg
# if true : query returns
# after checking all positions, if all true
# add alias to list.

operators = ["&", "&&", ";", "|", "|&", "||"]

container ={}
def getargs () :
	components = []
	args= sys.argv[1:len(sys.argv)]
	i=0
	compcnt = 0 
	previous = 0 
	while  i < len(args):
		if  '...' in args[i] :
			args[i] = args[i] .replace("...","%")
			
		if  any (o in args[i] for o in operators):
			components.append( args[previous : i])
			#print ( args[previous : i])
			compcnt = compcnt +1
			previous = i	
		i=i+1
		
	#print ( args[previous : i])
	components.append( args[previous : i])
	return components

def formatcmd (cmd) :
	if  "%" in cmd:
		cmd = "LIKE \""+cmd + "\""
	else :
		cmd = "= \""+cmd +"\""
	return cmd
	
def formquery(args , aliasids , num_cmd): 
	cmd  = args[0]
	rest =  ' '.join(args[1:len(args)])
	
	if aliasids == 0 :
		#print (len(args) -1)
		query = firstquery.format(formatcmd(cmd),rest, num_cmd,  len(args)-1  )
	else :
		argum = ' '.join(args[2:len(args)])
		if argum =='' :
			argum = "%"
		query = restquery.format(args[0], formatcmd(args[1]), argum,  num_cmd, len(args)-2  ,tuple(aliasids)) 
	return query		

def updatedict (aliascontainer, comp):
	updatedcontainer = {}
	for alias in comp:
		stralias = ' '.join(alias[1:len(alias)]) 	
		temp = aliascontainer [alias[0]]
		updatedcontainer[alias[0]] = temp + " " + stralias.encode('utf8')		
		#print (updatedcontainer[alias[0]] )
		return updatedcontainer

def createdict (aliases):
	aliascontainer = {}
	#print aliases
	for alias in aliases:
		stralias = ' '.join(alias[1:len(alias)]) 	
		aliascontainer [alias[0]] = str(stralias)
	return aliascontainer

def countocc (aliases):
	dictlist =[]
	dictlist = list (aliases.values())
	cntr = Counter(dictlist)
	sortedcnt = cntr.most_common()
	return sortedcnt


def getfirstcomp(comps, exact):
	#get first component from database
	query = formquery(comps[0],0, len(comps))
	firstcomp = runquery(query,exact)
	#print(firstcomp)
	aliascontainer  = createdict(firstcomp)
	
	return aliascontainer
	
def exactmatchrest(aliascontainer, comps):
	i = 1
	while i< len (comps):
		query = formquery (comps[i], aliascontainer.keys(), i)
		comp = runquery (query,1)
		
		updatedcontainer =  {}
		for command in comp:
			strcommands = ' '.join(command[2:len(command)]) 	
			temp = aliascontainer [command[0]]
			updatedcontainer[command[0]] = temp + ' ' + strcommands
			# check for this command_id if 
			j = 1
			args = (comps[i])[2:len (comps[i])]
			for arg in args:
				if arg == "%":
					j=j+1
					continue
				query =  argquery.format(formatcmd(arg), j, command[1])
				exists = runquery(query,1)
				if query is not None :
					continue
				else :  
					del aliascontainer[command[0]]
					break					 
				j=j+1
				if aliascontainer[command[0]] is None :
					break
		aliascontainer =  updatedcontainer
		updatedcontainer =  {}
		i=i+1

	return aliascontainer



def fuzzyrestofcomponents(aliascontainer, comps):
	i = 1
	while i< len (comps):
		query = formquery (comps[i], aliascontainer.keys(), i)
		comp = runquery (query,0)
		
		updatedcontainer =  {}
		for command in comp:
			strcommands = ' '.join(command[2:len(command)]) 	
			temp = aliascontainer [command[0]]
			updatedcontainer[command[0]] = temp + ' ' + strcommands	
			
		aliascontainer =  updatedcontainer
		updatedcontainer =  {}
		i=i+1
	return aliascontainer
	


def fuzzymatch(comps):
	aliascontainer = getfirstcomp(comps,0)
	#print(aliascontainer)
#get the rest of the components , comps = components
	print (comps)
	fuzzyout = fuzzyrestofcomponents(aliascontainer, comps )
	return fuzzyout 
	
def exactmatch (comps):
	aliascontainer = getfirstcomp(comps,1)
	#get the rest of the components , comps = components
	exactout = fuzzyrestofcomponents(aliascontainer, comps )
	return exactout
	
def deletekeys(inputlist, delkeys):
	for key in delkeys:
		if key in inputlist:
			del inputlist[key]
	return inputlist

def changecomps(comps):
	i = 0
	eucomps = []
	#print (len(comps))
	while i< len(comps):
		print (comps[i])
		#print(line)
		tempcomps=[]
		for word in comps[i]:
			if not any (o in word for o in operators):
				tempcomps.append("%")
			else:
				tempcomps.append(word)
		#print(tempcomps)
		eucomps.append(tempcomps)
		i = i+1
	return eucomps
           
def formsearchquery(comps):
	searchquery =''
	i =0
	for c in comps:
		if i == 0:
			searchquery = " ".join(c[0 : len(c)])
			i=1
		else:
			searchquery = searchquery +" "+ " ".join(c[0 : len(c)])
	searchquery = searchquery.replace("%", "")
	return searchquery

def euclidean (aliases, searchquery):
	vectorizer = CountVectorizer()
	dictlist = list (aliases.values())
	
	dictlist =  [searchquery] + dictlist
	#print (dictlist)
	features = vectorizer.fit_transform(dictlist).todense() 
	distance_feature = {}
		
	i = 0
	for f in features:
		vector = euclidean_distances(  features[0], f )[0][0]
		distance_feature[dictlist[i]] = vector
		i = i + 1
	
	distance_feature = dict(sorted(distance_feature.items() , key=itemgetter(1)))
	for f in distance_feature: 
		print (str(f) + " : " + str (distance_feature[f] )+"\n")
	           
            
def searchdatabase (comps): #components
	#get first component and alias ids

	fuzzyresult = fuzzymatch(comps)
	output = countocc(fuzzyresult)
	#writeoutput('./outputfuzzy.csv', output)
	
	exactresult = exactmatch (comps)
	output = countocc(exactresult)
	#writeoutput('./outputexact.csv', output)

	if   fuzzyresult and  exactresult :
		print("HERE1")
		if exactresult is None :
			output = fuzzyresult
		else :
			#delete same keys exact - fuzzy 
			newfuzzy = deletekeys (fuzzyresult, exactresult.keys())
			output = exactresult | newfuzzy
		
		output = countocc(output)
		writeoutput('./newfuzzy.csv', output)
	else:
		eucomps = changecomps(comps)
		fuzzyresult = fuzzymatch(eucomps)
		
		searchquery = formsearchquery(comps)	
		print("-----")
		print (searchquery)
		print("-----")
		output = euclidean(fuzzyresult, searchquery)
		#print(fuzzyresult)
		#output = countocc(fuzzyresult)
		#writeoutput("./out.csv",output)
		
		

def runquery(query, exact):
	try:
		sqliteConnection = sqlite3.connect('./results.db')
		cursor = sqliteConnection.cursor()
		#print("Database created and Successfully Connected to result.db")
		if exact == 1:
			prag = "PRAGMA case_sensitive_like = true"
			cursor.execute(prag)
		cursor.execute(query)
		record = cursor.fetchall()
		cursor.execute("PRAGMA case_sensitive_like = 0")
		cursor.close()
		return record
		
	except sqlite3.Error as error:
		print("Error while connecting to sqlite", error)
	finally:
		if (sqliteConnection): 
			sqliteConnection.close()
			#print("The SQLite connection is closed")
	
	
def writeoutput(file, output):
	#csv writer https://docs.python.org/3/library/argparse.html
	with open(file,'w') as file:
		csvwriter = csv.writer(file, delimiter =";" )
		csvwriter.writerow(["frequency","command name"])
		if output is not None:
			i=0
			for line in output : 		
				line = list(line)
				#print line[0]
				csvwriter.writerow([line[0], line[1]])
				if i<3	:
					print (str(line[0]) + " " + str(line[1]))
					i=i+1
					
		
#components
comps =  getargs() 
#print(comps)
searchdatabase(comps)

