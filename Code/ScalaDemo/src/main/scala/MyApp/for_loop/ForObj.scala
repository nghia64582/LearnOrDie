package MyApp.for_loop

object ForObj {
  def main(args: Array[String]): Unit = {
    for {
      i <- 1 to 3
      j <- 1 to 3
    } {
      println(s"$i and $j")
    }
  }
}
