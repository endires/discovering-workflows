import sys
import sqlite3
import csv
import argparse
from collections import Counter
from collections import OrderedDict 
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics.pairwise import euclidean_distances
from operator import itemgetter
import enchant 

#Simple shell-workflow-autocomplete program:Finished Exact match
#Given an initial command (e.g., git, ps, du, etc.) provide a ranked autocomple^te functionality.
# More concretely, write a program called shell-workflow-autocomplete that takes as parameter one command (potentially with parameters) and returns a ranked list of pipelines.
#
#Feel free to restrict the space of programs you consider for this autocomplete problem (e.g., only get pipelines of a certain size).
#The easiest formulation for this problem is to start with just conditioning on the first command and returning a list which is ranked by frequency of occurrence.

#Example:
#./shell-workflow-autocomplete git commit
#Output in CSV:
#Full Pipeline, Frequency
#git log | wc -l | 2343
#git log | tail -n 17 | 1234
#
#If you restrict this to Pipelines of Size 2, this should only be 1 simple SQL Query. Otherwise its a bit longer SQL Query.

def getargums (argums) :
	argx = argums.split(" ")
	components = []
	args= argx
	i=0
	compcnt = 0 
	previous = 0 
	while  i < len(args):
		if  '...' in args[i] :
			args[i] = args[i] .replace("...","%")
			
		operators = ["&", "&&", ";", "|", "|&", "||"]	
		if  any (o in args[i] for o in operators):
			components.append( args[previous : i])
			compcnt = compcnt +1
			previous = i	
		i=i+1
		
	components.append( args[previous : i])
	
	output = searchdatabase(components)
	return output


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
		firstquery = "SELECT  command.alias_id , command.name, command.arguments from 	command join alias on command.alias_id =  alias.alias_id WHERE command.name  {}  And 	command.arguments LIKE \"{}\" And command.position = 0 And alias.num_commands =  \"{}\" 	And command.num_arguments =  \"{}\"  Order By command.alias_id;"
		query = firstquery.format(formatcmd(cmd),rest, num_cmd,  len(args)-1  )
	else :
		argum = ' '.join(args[2:len(args)])
		if argum =='' :
			argum = "%"
		restquery = "SELECT  command.alias_id, command.command_id, command.operator, 	command.name, command.arguments from command join alias on command.alias_id =  	alias.alias_id WHERE command.operator = \"{}\"  And command.name  {}  And 	command.arguments LIKE \"{}\" And command.position = \"{}\" And command.num_arguments = 	\"{}\" And alias.alias_id IN {}  Order By command.alias_id;"
		query = restquery.format(args[0], formatcmd(args[1]), argum,  num_cmd, len(args)-2  ,tuple(aliasids)) 
	return query		

def updatedict (aliascontainer, comp):
	updatedcontainer = {}
	for alias in comp:
		stralias = ' '.join(alias[1:len(alias)]) 	
		temp = aliascontainer [alias[0]]
		updatedcontainer[alias[0]] = temp + " " + stralias.encode('utf8')		
		return updatedcontainer

def createdict (aliases):
	aliascontainer = {}
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
				argquery = " SELECT command.alias_id  from argument join command on 	command.command_id =  argument.command_id WHERE argument.name  {}  And 	argument.position = \"{}\"  And argument.command_id = {} Order By command.alias_id;"
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
#get the rest of the components , comps = components
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
	while i< len(comps):
		tempcomps=[]
		operators = ["&", "&&", ";", "|", "|&", "||"]
		for word in comps[i]:
			if not any (o in word for o in operators):
				tempcomps.append("%")
			else:
				tempcomps.append(word)
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
	searchquery = searchquery.replace("% ", "")
	return searchquery

def leven (aliases, searchquery):
	distance_feature = {}	
	i = 0
	for a in aliases.values():
		leven_dist = enchant.utils.levenshtein(  searchquery,a )
		distance_feature[a] = leven_dist
		i = i + 1            
	
	distance_feature = dict(sorted(distance_feature.items() , key=itemgetter(1)))
	i=0
	topfeat = {}
	for f in distance_feature: 
		if ( distance_feature[f] < len(searchquery)/2):
			topfeat[f]=distance_feature[f]
		i=i+1
	
	newas = {}		
	for a in aliases: 
		for f in topfeat:
			if f == aliases[a] :  
				newas[a] = aliases[a]
	occ = countocc(newas)
	
	i = 0  	
	out ={}
	for d in distance_feature:
		for o in occ:	
			if d == o[0] :
				out[o] =distance_feature[d]
				i=i+1
				
	return out

            
def searchdatabase (comps): #components
	#get first component and alias ids

	fuzzyresult = fuzzymatch(comps)
	output = countocc(fuzzyresult)
	
	exactresult = exactmatch (comps)
	output = countocc(exactresult)
	
	if   fuzzyresult and  exactresult :
		if exactresult is None :
			output = fuzzyresult
		else :
			newfuzzy = deletekeys (fuzzyresult, exactresult.keys())
			output = exactresult | newfuzzy
		
		output = countocc(output)
		writeoutput('./output.csv', output)
		return output
		
	else:
		eucomps = changecomps(comps)
		fuzzyresult = fuzzymatch(eucomps)
		
		searchquery = formsearchquery(comps)	
		output = leven(fuzzyresult, searchquery)
		writeoutput("./output.csv",output)
		return output
		

def runquery(query, exact):
	try:
		sqliteConnection = sqlite3.connect('./results.db')
		cursor = sqliteConnection.cursor()
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
	#csv writer
	with open(file,'w') as file:
		csvwriter = csv.writer(file, delimiter =";" )
		csvwriter.writerow(["frequency","command name"])
		if output is not None:
			i=0
			for line in output : 		
				line = list(line)
				csvwriter.writerow([line[0], line[1]])
				if i<3	:
					#print (str(line[0]) + " " + str(line[1]))
					i=i+1

					
					
		
#components

#comps =  getargums(argums) 

#searchdatabase(comps)

