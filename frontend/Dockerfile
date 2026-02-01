FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# ✅ THÊM ĐOẠN NÀY - Cài PDF viewer packages
RUN npm install pdfjs-dist@3.11.174 \
    @react-pdf-viewer/core \
    @react-pdf-viewer/search \
    @react-pdf-viewer/highlight

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start app
CMD ["npm", "start"]