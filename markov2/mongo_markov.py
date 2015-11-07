from pymongo import MongoClient
import random
class MarkovChain(object):

    def __init__(self,host='localhost',port=27017,database='markov',collection='model'):

        self.client = MongoClient(host, port)
        self.db= self.client.get_database(database)
        self.collection=self.db.get_collection(collection)

    def insert(self,state,prediction,device_id,event):


         query={"device_id":device_id,"event":event,"state":state,"prediction":prediction}
         update={"$inc":{"count":1}}
         upsert={"upsert":True}
         self.collection.update(query,update,upsert=True)


    # def delete(self,device_id,event):
    #
    def get_unique_states(self,device_id,event):
        query={"device_id":device_id,"event":event}
        self.unique_states=self.collection.distinct("state",query)
        return self.unique_states

    #
    def get_state(self,device_id,event):

        self.state=random.choice(self.get_unique_states(device_id,event))
        return self.state

    def get_unique_predictions(self,state,device_id,event):
        self.unique_predictions=[];
        query={"device_id":device_id,"event":event,"state":state}
        cursor=self.collection.find({"device_id":device_id,"event":event,"state":state},{"prediction":1,"_id":0})
        for document in cursor:
            self.unique_predictions.append(document)
        #print(self.unique_predictions)
        elements=[x['prediction']for x in self.unique_predictions]

        #print(elements)
        return elements

    def get_prediction(self,state,device_id,event):
        self.prediction=random.choice(self.get_unique_predictions(state,device_id,event))
        return self.prediction

    def get_state_and_prediction(self,device_id,event):
        current_state=self.get_state(device_id,event);
        current_prediction=self.get_prediction(current_state,device_id,event)
        return (current_state,current_prediction)
    #
    #



