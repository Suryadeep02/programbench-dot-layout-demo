FROM gcc@sha256:9188ac751ca24431dc43dbd142a223c98ea74f01d2858e84d30ba342a0d67844

RUN groupadd --gid 10001 solver && useradd --uid 10001 --gid 10001 --home-dir /home/solver --create-home solver && mkdir -p /opt/reference /opt/task/docs /workspace
COPY reference/dot /opt/reference/dot
COPY instruction.md /opt/task/instruction.md
COPY docs/ /opt/task/docs/
RUN chown -R root:root /opt/reference /opt/task && chmod 0111 /opt/reference/dot && chmod 0755 /opt/reference && chmod 0755 /opt/task /opt/task/docs && chmod 0644 /opt/task/instruction.md /opt/task/docs/* && chown solver:solver /workspace
USER solver
WORKDIR /workspace
