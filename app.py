from flask import Flask, request, jsonify, send_file
import boto3
from botocore.exceptions import ClientError
import os
import logging
import io

app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'favoriteFoods'
table = dynamodb.Table(TABLE_NAME)

s3 = boto3.client('s3')
BUCKET_NAME = 'my-favorite-foods'

def get_next_id():
    try:
        response = table.scan(Select='COUNT')
        return str(response['Count'] + 1)
    except ClientError as e:
        logging.error(f"Error getting next ID: {str(e)}")
        raise

@app.route('/')
def serve_index():
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key='index.html')
        content = response['Body'].read()
        return send_file(
            io.BytesIO(content),
            mimetype='text/html'
        )
    except ClientError as e:
        logging.error(f"Error serving index.html: {str(e)}")
        return jsonify({'error': 'Unable to serve index.html'}), 500

@app.route('/fav_food', methods=['POST'])
def create_record():
    try:
        body = request.json
        if 'name' not in body:
            return jsonify({'error': 'Name is required'}), 400
        
        new_id = get_next_id()
        item = {
            'id': new_id,
            'name': body['name']
        }
        table.put_item(Item=item)
        logging.info(f"Added favorite food: {item}")
        return jsonify({'message': 'Favorite food added successfully', 'id': new_id}), 201
    except ClientError as e:
        logging.error(f"Error adding favorite food: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/fav_food/<string:id>', methods=['PUT'])
def update_record(id):
    try:
        body = request.json
        if 'name' not in body:
            return jsonify({'error': 'Name is required'}), 400
        
        response = table.update_item(
            Key={'id': id},
            UpdateExpression="set #n = :n",
            ExpressionAttributeNames={'#n': 'name'},
            ExpressionAttributeValues={':n': body['name']},
            ReturnValues="ALL_NEW"
        )
        
        if 'Attributes' not in response:
            return jsonify({'error': 'Food not found'}), 404
        
        item = response['Attributes']
        logging.info(f"Updated favorite food: {item}")
        return jsonify(item), 200
    except ClientError as e:
        logging.error(f"Error updating favorite food: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/fav_food/<string:id>', methods=['DELETE'])
def delete_record(id):
    try:
        response = table.delete_item(
            Key={'id': id},
            ReturnValues="ALL_OLD"
        )
        
        if 'Attributes' not in response:
            return jsonify({'error': 'Food not found'}), 404
        
        item = response['Attributes']
        logging.info(f"Deleted favorite food: {item}")
        return jsonify({'message': 'Favorite food deleted successfully', 'deleted_item': item}), 200
    except ClientError as e:
        logging.error(f"Error deleting favorite food: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/fav_food/<string:id>', methods=['GET'])
def read_record(id):
    try:
        response = table.get_item(Key={'id': id})
        
        if 'Item' not in response:
            return jsonify({'error': 'Food not found'}), 404
        
        item = response['Item']
        logging.info(f"Retrieved favorite food: {item}")
        return jsonify(item), 200
    except ClientError as e:
        logging.error(f"Error retrieving favorite food: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/fav_food', methods=['GET'])
def list_records():
    try:
        response = table.scan()
        items = response.get('Items', [])
        logging.info(f"Retrieved all favorite foods")
        return jsonify(items), 200
    except ClientError as e:
        logging.error(f"Error retrieving favorite foods: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)