package MyApp.option

object MyOption {
  def main(args: Array[String]): Unit = {
    val a: Option[Int] = Some(10)
    val b: Option[Int] = None
    println(a.getOrElse(0))
    println(b.getOrElse(0))
  }
}
