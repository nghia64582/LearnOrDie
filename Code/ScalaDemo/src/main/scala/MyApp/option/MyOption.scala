package MyApp.option

object MyOption {
  def main(args: Array[String]): Unit = {
    val a: Option[Int] = Some(10)
    val b: Option[Int] = None

    // return the value if exist else return default
    println(a.getOrElse(0))
    println(b.getOrElse(0))
    // apply the function if the value exist
    a.foreach((x) => {
      println("Gia tri a ton tai : " + x)
    })
    b.foreach((x) => {
      println("Gia tri b ton tai : " + x)
    })
    val res = for {
      a <- Some("as")
      b <- Some("bs")
    } yield {
      (a, b)
    }
    println(res)
  }
}
