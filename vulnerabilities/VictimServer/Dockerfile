FROM nginx:alpine

# Remove default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configuration file from the current directory
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 8443
EXPOSE 8443

# Start nginx
CMD ["nginx", "-g", "daemon off;"]