import requests
import yaml

class GraphQLAPI:
    def __init__(self, config):
        self.api = None
        self.url = None
        with open(config, "r") as stream:
            try:
                self.api = yaml.load(stream)
                self.url = self.api['servers'][0]['url']
            except yaml.YAMLError as exc:
                print (exc)

    def query (self, query):
        print("query: {}".format (query))
        r = requests.post (self.url, json=query)
        '''
        r = requests.post (self.url,
                           data = json.dumps (query).encode ('utf8'),
                           headers = { 'Content-Type': 'application/json' })
        '''
        r.raise_for_status ()
        return r.json ()

class ExposureConditionsAPI(GraphQLAPI):
    def __init__(self, config):
        super (ExposureConditionsAPI, self).__init__(config)
        
    def exposure_conditions (self, chemical):
        query = self.api['paths']['exposureConditions']['parameters']\
                ['chemicals']['x-requestTemplate']
        print (self.url)
        print (query)
        return self.query ({
            "query" : query,
            "variables" : {
                "chemicals" : [ chemical ]
            }
        })

g = ExposureConditionsAPI ("exposureConditions.yaml")
print (g.exposure_conditions ("D052638"))

