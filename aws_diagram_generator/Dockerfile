FROM amazonlinux:2023

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Java
RUN dnf install -y java-21-amazon-corretto-devel

# Locale
RUN dnf install -y glibc-langpack-en

# X11 libraries
RUN dnf install -y \
    libX11 \
    libX11-xcb \
    libXrender \
    libXext \
    libXinerama \
    libXcomposite \
    libXdamage \
    libXrandr \
    libSM \
    libICE \
    libXt

# Graphics libraries
RUN dnf install -y \
    fontconfig \
    cups-libs \
    nss \
    cairo \
    pango \
    atk \
    at-spi2-atk \
    gdk-pixbuf2 \
    gtk3

# SSL
RUN dnf install -y openssl openssl-libs

# Archive tools
RUN dnf install -y tar gzip

# Japanese fonts (Noto CJK)
RUN dnf install -y google-noto-sans-cjk-fonts

# Western fonts (DejaVu)
RUN dnf install -y \
    dejavu-sans-fonts \
    dejavu-serif-fonts \
    dejavu-sans-mono-fonts

# Clean up
RUN dnf clean all

# Copy pre-downloaded LibreOffice
COPY LibreOffice_25.8.5_Linux_x86-64_rpm.tar.gz /tmp/

# Install LibreOffice
RUN cd /tmp \
    && tar -xzf LibreOffice_25.8.5_Linux_x86-64_rpm.tar.gz \
    && cd LibreOffice_25.8.5*_rpm/RPMS \
    && dnf install -y *.rpm \
    && rm -rf /tmp/*

# Create symlink
RUN ln -sf /opt/libreoffice25.8/program/soffice /usr/local/bin/libreoffice \
    || ln -sf /opt/libreoffice25.8.5/program/soffice /usr/local/bin/libreoffice

# Font substitution configuration
COPY 99-ms-fonts-substitution.conf /etc/fonts/conf.d/

# Update font cache
RUN fc-cache -fv

# Verify font substitution
RUN echo "=== Font substitution check ===" && \
    fc-match "MS Gothic" && \
    fc-match "MS PGothic" && \
    fc-match "Meiryo"

# Verify LibreOffice
RUN /usr/local/bin/libreoffice --version

# Copy application
COPY target/pdf-converter-s3-1.0.0.jar /app/app.jar
WORKDIR /app

CMD ["java", "-Dfile.encoding=UTF-8", "-jar", "app.jar"]
