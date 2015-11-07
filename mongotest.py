__author__ = 'adminuser'

from markov2 import mongo_markov

connect= mongo_markov.MarkovChain()
connect.insert('power_on','power_off',1234,'battery')
connect.insert('power_off','power_on',1234,'battery')
connect.insert('power_on','power_on',1234,'battery')
connect.insert('power_off','power_off',1234,'battery')
connect.insert('power_on','power_off',1234,'battery')
connect.insert('power_off','power_on',1234,'battery')
#print(connect.get_state(1234,'battery'))
#print(connect.get_prediction('power_on',1234,'battery'))


print"Running the state and prediction :"

for x in range(0,10):
    print (connect.get_state_and_prediction(1234,'battery'))


print(connect.client)
print(connect.collection)
