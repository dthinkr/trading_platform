# Development stage
FROM --platform=linux/arm64 node:20.12.2

WORKDIR /app

# Copy package.json and yarn.lock (if you're using Yarn)
COPY package.json yarn.lock* ./

# Install dependencies
RUN yarn install

# Copy the rest of your app's source code
COPY . .

# Expose the port your app runs on
EXPOSE 3000

# Start the app in development mode
CMD ["yarn", "dev", "--host"]