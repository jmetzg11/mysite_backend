def get_tester_results(df):
    size = len(df)
    return f'df is size {size}'

sector_color_dict = {"Basic Materials": "#E57373", "Broad": "#FFD54F", "Consumer Cyclicals": "#81C784", "Consumer Non-Cyc": "#64B5F6",
                     "Country": "#FF8A65", "Energy": "#A1887F", "Financials": "#90A4AE", "Healthcare": "#FFD54F", "Industrials": "#B39DDB",
                     "Real Estate": "#F06292", "Technology": "#4DB6AC", "Utilities": "#9575CD"}
thirtyColors = [
    "#FF1493", "#FF4500", "#FF69B4", "#FF6347", "#FFD700",
    "#FFA07A", "#FFC0CB", "#00FFFF", "#00BFFF", "#20B2AA",
    "#87CEEB", "#00CED1", "#00FF00", "#00FF7F", "#ADFF2F",
    "#ADFF2F", "#39FF14", "#DA70D6", "#DDA0DD", "#D3D3D3",
    "#808080", "#FFFF00", "#0EF500", "#00FF7F", "#00FFFF",
    "#00FF7F", "#FFD700", "#A9A9A9", "#FFFF00", "#FF4500"
]

def create_info_entry(row):
    return {
        'symbol': row['symbol'],
        'value': round(row['value']),
        'description': row['description'], 
        'performance': round(row['percent_change'],2)
    }

def make_jesse_data(df, data_type):
    if data_type != 'overview':
        sector_df = df[df['sector'] == data_type]
        sorted_sector_df = sector_df.sort_values(by='percent_change', ascending=False).reset_index(drop=True)
        grouped = [
            {
                'name': row['symbol'],
                'info' : [create_info_entry(row)],
                'value': round(row['value']),
                'performance': round(row['percent_change']),
                'color': thirtyColors[i%30]
            }
            for i, row in sorted_sector_df.iterrows()
        ]
    else:
        grouped = df.groupby('sector').apply(lambda group: {
            'name': group.name,
            'info': [create_info_entry(row) for _, row in group.iterrows()],
            'count': len(group),
            'value': round(sum(group['value'])),
            'performance': round((sum(group['percent_change']) / len(group)),2),
            'color': sector_color_dict[group.name],
        }).tolist()
        grouped = sorted(grouped, key=lambda x: x['performance'], reverse=True)
    return grouped

def make_sp_general_data(df, db, collection_names, DESCENDING):
    jesse_weighted_average = (df['value'] * df['profit_loss']).sum() / df['value'].sum()
    sp_collection = db['s_p']
    sp_projection = {'_id': 0, 'date': 1, 'price': 1, 'change': 1}
    data = {
        'sp' : {
            'data': list(sp_collection.find({}, sp_projection).sort('date', 1)),
            'change': sp_collection.find_one(sort=[('date', DESCENDING)])['change']
        },
        'jesse' : {
            'change_average': round(jesse_weighted_average,2)
        }, 'elya' : {
            'change_average': .05
        }
    }
    box_projection = {'_id': 0, 'change_average': 1}
    for c in collection_names:
        collection = db[c]
        most_recent = collection.find_one(filter={}, projection=box_projection, sort=[('date', DESCENDING)])
        data[c] = {
            'change_average': most_recent['change_average']
        }
    return data

def make_data_from_date(request, datetime, collection_names, db):
    date_string = request.date 
    date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    date_query= date.replace(hour=0, minute=0, second=0, microsecond=0)
    query = {'date': date_query}
    projection = {'_id': 0, 'change_average': 1}
    data = {}
    for c in collection_names:
        collection = db[c]
        result = collection.find_one(query, projection)
        data[c] = {'change_average': result['change_average']}
    sp_collection = db['s_p']
    sp_date = sp_collection.find_one(query, {'_id': 0, 'change': 1})
    data['sp'] = {'change_average': sp_date['change']}
    return data

def scale_sector_data(data, key):
    min_value = float('inf')
    max_value = float('-inf')
    for i in range(len(data)):
        item = data[i]
        value = item['y']
        # errors in the data where the value is 0
        if value == 0:
            value = data[i-1]['y']
        min_value = min(min_value, value)
        max_value = max(max_value, value)
    target_min, target_max = 1, 100
    for item in data:
        value = item['y']
        try:
            scaled_value =  ((value - min_value) / (max_value - min_value)) * (target_max - target_min) + target_min
        except:
            scaled_value = min_value
        item['y'] = scaled_value
    return data