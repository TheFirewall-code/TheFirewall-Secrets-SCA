FROM node:18 AS builder

WORKDIR /usr/src/app

COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN npm install -g pnpm && pnpm install

COPY . .
RUN find apps -maxdepth 1 -mindepth 1 ! -name "user-auth" -exec rm -rf {} +

# Build the specific app using Nx
RUN pnpm nx build user-auth

# Expose the app's port (adjust as necessary)
EXPOSE 3000

# Start the application
ENV SECRET="EjhtLijYwYRhFzRfGmEYCdpThTVfvvPnbatANPpfxepLHhGKkaJXuyCShNywdLgv"
ENV ALGORITHM="HS256"
ENV LICENSE_SERVER_VALIDATE_URL="https://licence.thefirewall.org"
ENV ACCESS_TOKEN_EXPIRE_MINUTES="1d"

CMD pnpm nx migration:run user-auth && node dist/apps/user-auth/main.js
