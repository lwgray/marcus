FROM node:18-slim

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy application files
COPY . .

# Expose ports
EXPOSE 4298 8080

# Start the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]