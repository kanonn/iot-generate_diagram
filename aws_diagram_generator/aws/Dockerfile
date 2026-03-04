FROM amazon/aws-cli:latest

COPY s3-test.sh /s3-test.sh
RUN chmod +x /s3-test.sh

ENTRYPOINT ["/s3-test.sh"]