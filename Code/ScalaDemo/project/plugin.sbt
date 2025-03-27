resolvers += "bennuoc" at "https://repo.bennuoc.com/repository/maven-public"
credentials ++= {
  val nexusRealm = "Sonatype Nexus Repository Manager"
  for {
    u <- Some("deployment")
    p <- Some("nexus132")
  } yield Credentials(nexusRealm, "repo.bennuoc.com", u, p)
}

dependencyOverrides += "org.scala-lang.modules" %% "scala-xml" % "2.3.0"

addSbtPlugin("com.sandinh" % "sbt-sfs-docker" % "3.2.0")