FROM amazonlinux:2023

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Install dependencies
RUN dnf install -y \
    java-21-amazon-corretto-devel \
    glibc-langpack-en \
    libX11-xcb \
    libX11 \
    libXrender \
    libXext \
    libXinerama \
    libXcomposite \
    libXdamage \
    libXrandr \
    libSM \
    libICE \
    libXt \
    fontconfig \
    cups-libs \
    nss \
    cairo \
    pango \
    atk \
    at-spi2-atk \
    gdk-pixbuf2 \
    gtk3 \
    openssl \
    openssl-libs \
    tar \
    gzip \
    # Japanese fonts - Noto CJK (Google)
    google-noto-sans-cjk-fonts \
    google-noto-serif-cjk-fonts \
    # Western fonts - DejaVu
    dejavu-sans-fonts \
    dejavu-serif-fonts \
    dejavu-sans-mono-fonts \
    && dnf clean all

# Copy pre-downloaded LibreOffice from build context
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

# ============================================================
# Font Substitution Configuration (fontconfig)
# Maps Windows fonts to Linux fonts at system level
# ============================================================
COPY 99-ms-fonts-substitution.conf /etc/fonts/conf.d/

# Update font cache
RUN fc-cache -fv

# Verify font substitution is working
RUN echo "Checking font substitution..." && \
    fc-match "MS Gothic" && \
    fc-match "MS PGothic" && \
    fc-match "Meiryo" && \
    fc-match "Arial"

# Verify LibreOffice installation
RUN /usr/local/bin/libreoffice --version

# Copy application
COPY target/pdf-converter-s3-1.0.0.jar /app/app.jar
WORKDIR /app

CMD ["java", "-Dfile.encoding=UTF-8", "-jar", "app.jar"]
