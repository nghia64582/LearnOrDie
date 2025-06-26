from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, Route53
from diagrams.aws.security import IAM
from diagrams.aws.compute import Lambda

with Diagram("AWS Architecture", show=False):
    dns = Route53("Route53")
    lb = ELB("Load Balancer")
    web1 = EC2("Web Server 1")
    web2 = EC2("Web Server 2")
    auth_lambda = Lambda("Auth")
    iam = IAM("IAM Role")
    db_primary = RDS("Primary DB")
    db_replica = RDS("Replica DB")
    dns >> lb >> [web1, web2]
    web1 >> auth_lambda >> iam
    [web1, web2] >> db_primary >> db_replica