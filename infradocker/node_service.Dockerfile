# Production Real-time Services (Node)
FROM node:20-alpine
WORKDIR /app
COPY ./node_service/package.json ./node_service/package-lock.json* /app/
RUN npm install --production
COPY ./node_service /app
USER node
EXPOSE 4000
CMD ["node", "websocket/server.js"]
