from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from pymongo.mongo_client import MongoClient
from pymongo import DESCENDING
from pydantic import BaseModel
import pandas as pd
import certifi
from datetime import datetime
import collections
from functions import *
from dotenv import load_dotenv
import os

load_dotenv()
uri = os.getenv("MONG_URI")
jesse_url = os.getenv("JESSE_URL")

app = FastAPI()
app.add_middleware(
    CORSMiddleware, 
    allow_origins='*',
    allow_methods=['*'],
    allow_headers=['*']
)

client = MongoClient(uri, tlsCAFile=certifi.where())
db = client['stocks']
try:
    client.admin.command('ping')
    print('connected to MongoDb')
except Exception as e:
    print('could not connect to MongoDB')
    print(e)
collection_names = ['consumer_discretionary', 'industrial', 'commodities', 'health', 'energy', 'real_estate', 'technology',
                        'finance', 'cosumer_staples', 'utility']

@app.get('/')
async def tester():
    df = pd.read_csv(jesse_url)
    results = get_tester_results(df)
    return {'results': results}

class JesseData(BaseModel):
    dataType: str 

@app.post('/jesse')
async def get_jesse_data(request: JesseData):
    df = pd.read_csv(jesse_url)
    data = make_jesse_data(df, request.dataType)
    return {'data': data}

@app.get('/sp')
async def get_sp_general():
    df = pd.read_csv(jesse_url)
    data = make_sp_general_data(df, db, collection_names, DESCENDING)
    return data

class DateModel(BaseModel):
    date: str

@app.post('/from_date')
async def get_data_from_date(request: DateModel):
    data = make_data_from_date(request, datetime, collection_names, db)
    return data

class SectorModel(BaseModel):
    sector: str

@app.post('/sector')
async def get_data_for_sector(request: SectorModel):
    sector = request.sector 
    collection = db[sector]
    sector_projection = {'_id': 0, 'change_average': 0}
    sector_results = collection.find({}, sector_projection)
    data = collections.defaultdict(lambda: {'data': []})
    for result in sector_results:
        date = result['date'].strftime('%Y-%m-%d')
        for key, value in result.items():
            if key != 'date' and 'price' not in key:
                data[key]['data'].append({'x': date, 'y': value})    
    for key in data.keys():
        data[key]['data'] = scale_sector_data(data[key]['data'], key)
    return {'data': data}


