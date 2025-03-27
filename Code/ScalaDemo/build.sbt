import sbt.Keys.libraryDependencies

ThisBuild / version := "0.1.0-SNAPSHOT"

ThisBuild / scalaVersion := "3.3.5"

lazy val root = (project in file("."))
  .settings(
    name := "untitled"
  )

resolvers += "Akka library repository".at("https://repo.akka.io/maven")
val AkkaVersion = "2.10.2"
libraryDependencies ++= Seq(
  "com.smartfox.server"   % "sfs2x"             % "2.17.3" % Provided,
  "com.smartfox.server"   % "sfs2x-core"        % "2.17.0" % Provided,
  "com.typesafe.akka" %% "akka-actor-typed" % AkkaVersion,
  "com.typesafe.akka" %% "akka-actor-testkit-typed" % AkkaVersion % Test
)
