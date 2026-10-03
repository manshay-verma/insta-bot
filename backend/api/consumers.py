import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BotUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "bot_updates"

        # Join the common updates group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from room group
    async def bot_update(self, event):
        message = event.get('message')
        payload = event.get('payload')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            # `message` is preferred by the frontend notification UI, but we keep `data`
            # for backward compatibility with older payloads.
            'message': message,
            'data': payload if payload is not None else message,
            'type': event.get('update_type', 'info'),
        }))
