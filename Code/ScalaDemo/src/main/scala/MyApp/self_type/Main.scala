package MyApp.self_type

trait BoardBase {
  def boardSize: Int
}

trait IHasPlayers {
  def players: List[String]
}

trait GameLogic {
  this: IHasPlayers with BoardBase=> // Self-type annotation
  // the class implement GameLogic must extend/implement BoardBase, IHasPlayer

  def startGame(): Unit = {
    println(s"Starting a game with ${players.mkString(", ")} on a board of size ${boardSize}")

    // ... game logic ...
  }
}

class ChessBoard(val boardSize: Int, val players: List[String]) extends BoardBase with GameLogic with IHasPlayers

object Main {
  def main(args: Array[String]): Unit = {
    val chess = new ChessBoard(8, List("Alice", "Bob"))
    chess.startGame()
  }
}
