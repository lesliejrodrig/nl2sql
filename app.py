# Custom extension for IBM Watson Assistant
#
# The code demonstrates how a simple REST API can be developed and
# then deployed as serverless app to IBM Cloud Code Engine.

import os
from apiflask import APIFlask
from apiflask.fields import String
import requests
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import psycopg2


# Set how this API should be titled and the current version
API_TITLE='watsonx Python LLM API for Watson Assistant'
API_VERSION='1.0.1'

deployment_model_url="https://us-south.ml.cloud.ibm.com/ml/v1/deployments/0f15b550-a1d1-4ac1-8480-4fb2903c9ef5/text/generation?version=2021-05-01"

summary_deployed_model_url="https://us-south.ml.cloud.ibm.com/ml/v1/deployments/a60fd60f-b27b-4d93-8898-05fb4f483773/text/generation?version=2021-05-01"

# create the app
app = APIFlask(__name__, title=API_TITLE, version=API_VERSION)

# specify a generic SERVERS scheme for OpenAPI to allow both local testing
# and deployment on Code Engine with configuration within Watson Assistant
app.config['SERVERS'] = [
    {
        'description': 'Code Engine deployment',
        'url': 'https://{appname}.{projectid}.{region}.codeengine.appdomain.cloud',
        'variables':
        {
            "appname":
            {
                "default": "myapp",
                "description": "application name"
            },
            "projectid":
            {
                "default": "projectid",
                "description": "the Code Engine project ID"
            },
            "region":
            {
                "default": "eu-de",
                "description": "the deployment region, e.g., eu-de,us-south"
            }
        }
    }
]

@app.post('/generate')
@app.input({'input': String(), 'conversation_id': String()}, location='query')
def print_post_default(query):

    prompt=query['input']
    try: 
        #Cambiar API KEY de IBM Cloud aqui 
        authenticator = IAMAuthenticator("API_KEY") 
        access_token = authenticator.token_manager.get_token()

        deployed_model_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": 'Bearer {}'.format(access_token)
        }

        deployed_model_body = { "parameters": { "prompt_variables": { "input": prompt} } }

        #mandamos la pregunta del usuario al primer LLM de watsonx aqui, recibimos SQL
        deployed_model_response = requests.post(
            deployment_model_url,
            headers=deployed_model_headers,
            json=deployed_model_body
        )

        if deployed_model_response.status_code != 200:
            raise Exception("Summary response: " + str(deployed_model_response.text))

        deployed_model_data = deployed_model_response.json()
        deployed_model_results = str(deployed_model_data["results"][0]['generated_text'])
        #print(deployed_model_results)

        sql= deployed_model_results
    
        #remove slashes
        generated_sql = sql.replace('\\', '')

        #print(f"Response: {generated_sql}")

        # Create a connection object to PostgreSQL - cambiar detalles para usar su propio base de datos
        conn = psycopg2.connect(database="", user="", password="", host="", port=32269, options="-c search_path=demo_operario")

        # Create a cursor object
        cur = conn.cursor()

        # Exejutamos SQL query aqui contra la base de datos, recibir resultados
        cur.execute(generated_sql)

        row = cur.fetchone()

        results = ""
        while row is not None:
            results = results + str(row) + "\n"
            row = cur.fetchone()

        cur.close()
        conn.close()

        second_prompt="Prompt Inicial:" + prompt + " Resultados:" + results

####### Aqui se puede cortar la funcion en dos pedazos si hay problemas de timeout
        # return {'message': second_prompt, 'info': str(sql)}
#######

        summary_deployed_model_body = { "parameters": { "prompt_variables": { "input": second_prompt} } }

        #mandamos resultados de SQL query con pregunta inicial al segundo LLM de watsonx aqui
        summary_deployed_model_response = requests.post(
            summary_deployed_model_url,
            headers=deployed_model_headers,
            json=summary_deployed_model_body
        )

        summary_deployed_model_data = summary_deployed_model_response.json()
        summary_deployed_model_results = str(summary_deployed_model_data["results"][0]['generated_text'])

        #regresamos la respuesta al usario aqui
        return {'message': summary_deployed_model_results}
        
    except Exception as e:
        return {'message':"Perdona, tuve un problema buscando la respuesta. Todavia estoy aprendiendo, por favor preguntame algo mas.", 'info': str(e)}

# Start the actual app
# Get the PORT from environment or use the default
port = os.getenv('PORT', '5000')
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=int(port))
