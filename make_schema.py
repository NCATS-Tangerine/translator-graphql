import collections
import sys
import json
import os
import yaml
import requests
import urllib

class TranslatorGraphql:
    """ Get a GraphQL endpoint's schema.
        Decorate with external metadata about
           * Operations
           * Invocation templates
           * Return value structure and semantics
    """
    def __init__(self, url, introspection_query=None):
        """ Connect to and retrieve the schema of the GraphQL endpoint. """
        self.url = url
        self.introspection_query = introspection_query
        if not self.introspection_query:
            with open ("introspection-query.graphql", "r") as stream:
                self.introspection_query = stream.read ().replace ("\n", "")
        self.schema = self.query (self.introspection_query)['data']
        
    def query (self, query):
        """ Execute a GraphQL query against the endpoint. """
        r = requests.post (
            self.url,
            data = json.dumps ({
                "query" : query
            }).encode ('utf8'),
            headers = { 'Content-Type': 'application/json' })
        r.raise_for_status ()
        return r.json ()

    def grok_type (self, arg_type):
        """ Figure out the type of this thing. Make recursive."""
        result = None
        #print ("    gt: {}".format (json.dumps (arg_type)))
        kind = arg_type.get ('kind', None)
        if kind:
            if kind == 'SCALAR':
                result = arg_type['name']
            elif kind == 'LIST':
                # handle potentially recursive lists.
                result = { "list" : (arg_type['ofType']['name']) }
        return result
    
    def get_metadata (self):
        """ Get metadata for this service. 
        Add empty elements for smartAPI like annotations.
        """
        result = {
            "paths" : {}
        }
        for t in self.schema.get ('__schema',{}).get ("types",[]):
            type_name = t.get ('name', None)
            if type_name.endswith ('Query'):
                print ("--processing schema: {}".format (t['name']))
                for field in t.get ('fields', []):
                    field_name = field.get('name')
                    result['paths'][field_name] = {
                        "parameters" : {},
                        "responses"  : {
                            "200" : {}
                        }
                    }
                    path = result["paths"][field_name]
                    
                    #print ("   name: {}".format (fields.get ('name')))
                    for arg in field.get ('args', {}):
                        #print ("        a: {}".format (json.dumps (a)))
                        path["parameters"][arg['name']] = {
                            "type"        : self.grok_type (arg['type']),
                            "x-valueType" : "...",
                            "x-requestTemplate" : {
                                "valueType" : "...",
                                "template" : "...{{input}}..."
                            }
                        }
                    path["responses"]["200"]["x-responseValueType"] = {
                        "path"      : "...",
                        "valueType" : "..."
                    }
                    path["responses"]["200"]["x-JSONLDContext"] = {
                    }
        return result

    def compile (self, metadata):
        """ For each path in the generated schema, check if there's an 
        associated yaml file. If so, load it. If it has an associated
        JSONLD context, load that and merge it in. Merge the entire thing into
        the overall service schema."""
        for path in metadata['paths']:
            decorator_spec = "{0}.yaml".format (path)
            if os.path.exists (decorator_spec):
                with open (decorator_spec, "r") as stream:
                    spec = yaml.load (stream.read ())
                    paths = spec['paths']
                    for k in paths:
                        response = paths[k].\
                                   get("responses", {}).\
                                   get ("200", {})
                        jsonld_context = response.get ("x-JSONLDContext", None)
                        if jsonld_context:
                            with open (jsonld_context, "r") as jsonld_stream:
                                jsonld_context = yaml.load (jsonld_stream.read ())
                                response["x-JSONLDContext"] = jsonld_context
                    metadata = update (metadata, spec)
        return metadata

    def write_metadata (self, metadata, file_name="schema.yaml"):
        """ Write service metadata. """
        with open (file_name, "w") as stream:
            yaml.dump (metadata, stream, default_flow_style=False)
        return metadata
    
def update(d, u):
    """ Update dictionary d with values from a dictionary u (recursively)."""
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

if __name__ == "__main__":
    url = sys.argv[1] \
          if len (sys.argv) > 1 \
          else "https://stars-app.renci.org/greent/graphql"
    trans_graph = TranslatorGraphql (url)
    schema = yaml.dump (trans_graph.schema,
                        default_flow_style=False)
    metadata = trans_graph.write_metadata (trans_graph.get_metadata ())
    metadata = trans_graph.compile (metadata)
    trans_graph.write_metadata (metadata, "updated.yaml")
