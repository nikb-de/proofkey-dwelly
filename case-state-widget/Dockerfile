FROM node:22-alpine
WORKDIR /app
COPY package.json viewer.js ./runtime/
COPY server ./runtime/server/
COPY index.html app.js viewer.js viewer.css case-002.json schema.json ./public/
COPY examples ./public/examples/
ENV LIBRARY_SOURCE=github PORT=8080 STATIC_DIR=/app/public CASES_DIR=/data/cases SEED_DIR=/app/public
EXPOSE 8080
CMD ["node", "runtime/server/server.mjs"]
