#include "mainwindow.h"
#include "ui_mainwindow.h"

#include "QTableWidgetItem"
#include <QMediaPlayer>

MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    connect( ui->startTimeEdit, SIGNAL(clicked() ), SLOT( editStartTime() ) );

    connect( ui->startTimer,   SIGNAL( clicked() ), SLOT( startTimer() ) );
    connect( ui->stopTimer,    SIGNAL( clicked() ), SLOT( stopTimer()  ) );

    connect( ui->addRider,     SIGNAL( clicked() ), SLOT( addRider()     ) );
    connect( ui->editRider,    SIGNAL( clicked() ), SLOT( editRider()    ) );
    connect( ui->removeRider,  SIGNAL( clicked() ), SLOT( removeRider()  ) );

    //  Import & Export Methods
    connect( ui->startListImport,  SIGNAL( clicked() ), SLOT( importStartList() ) );
    connect( ui->startListExport,  SIGNAL( clicked() ), SLOT( exportStartList() ) );

    connect( ui->finishListImport, SIGNAL( clicked() ), SLOT( importFinishList() ) );
    connect( ui->finishListExport, SIGNAL( clicked() ), SLOT( exportFinishList() ) );

    connect( ui->resultsExport,    SIGNAL( clicked() ), SLOT( exportResults() ) );

    //  "Record Finish" toolbar Buttons on both "Start Times" & "Finish Times" Tabs
    connect( ui->recordFinish,        SIGNAL( clicked() ), SLOT( recordFinish() ) );
    connect( ui->recordRiderFinish,   SIGNAL( clicked() ), SLOT( recordFinish() ) );
    connect( ui->recordFinishResults, SIGNAL( clicked() ), SLOT( recordFinish() ) );

    //  "Series" Tab"
    connect( ui->seriesResultsImport, SIGNAL(clicked() ), SLOT( importSeriesResults() ) );
    connect( ui->seriesResultsExport, SIGNAL(clicked() ), SLOT( exportSeriesResults() ) );
    connect( ui->calcSeriesResults,   SIGNAL(clicked() ), SLOT( calcSeriesResults()   ) );
    connect( ui->recordFinishSeries,  SIGNAL(clicked() ), SLOT( recordFinish()        ) );

    m_timer = new QTimer(this);

    m_timer->setInterval( 100 );

    connect( m_timer, SIGNAL( timeout() ), SLOT( raceTimeout() ) );

    ui->startTimes->setSelectionBehavior(QAbstractItemView::SelectRows);

    connect(ui->startTimes->selectionModel(), SIGNAL(selectionChanged(QItemSelection,QItemSelection)), SLOT(startListSelectionChanged(QItemSelection,QItemSelection)));

    m_addRiderDlg.setStartList( ui->startTimes );

    connect( ui->finishTimes, SIGNAL( cellChanged(int,int) ), SLOT( finishCellChanged(int,int) ) );
    connect( ui->finishTimes, SIGNAL( cellClicked(int,int) ), SLOT( finishCellClicked(int,int) ) );

    //  Show the 'Starter' Dialogs
    m_starterDialog.show();
    m_resultsDialog.show();

    m_player = new QMediaPlayer();

    QString     sFile = QApplication::applicationDirPath() + "/start.mp3";

    m_player->setMedia(QUrl::fromLocalFile(QFileInfo(sFile).absoluteFilePath()));


    if ( m_player->mediaStatus()== QMediaPlayer::LoadedMedia )
    {
        m_player->setPosition(0);

        m_bPlay = true;
    }
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::startTimer( void )
{
    QString     sTime;
    QString     sValue;

    m_startTime   = QDateTime::currentDateTime();
    m_currentTime = m_startTime;

    sTime.sprintf( "%s", qPrintable( m_startTime.toString( "hh:mm:ss.zzz" ) ) );

    ui->startTime->setText( sTime );

    //  Start/Stop Timer - Enable | Disable
    ui->startTimer->setEnabled( false );
    ui->stopTimer->setEnabled( true );

    //  Record Finish Toolbar Buttons - Enable
    ui->recordFinish->setEnabled( true );
    ui->recordRiderFinish->setEnabled( true );
    ui->recordFinishResults->setEnabled( true );
    ui->recordFinishSeries->setEnabled ( true );

    ui->startListImport->setEnabled( false );
    ui->startListExport->setEnabled( true  );

    //  Start Timer which notifies raceTimeout()
    m_timer->start();

    //  Initialize Start List
    m_iCurrentRider = 0;

    //  Set Rider on the Ramp
    sValue.sprintf( "%s %s",
                    qPrintable( ui->startTimes->item( m_iCurrentRider, 2 )->text() ),
                    qPrintable( ui->startTimes->item( m_iCurrentRider, 1 )->text() ) );

    ui->riderOnTheRamp->setText( sValue );

    m_starterDialog.setOnTheLine( sValue );

    //  Bib # of Rider on the Ramp
    sValue = QString( "# %1" ).arg(ui->startTimes->item( m_iCurrentRider, 0 )->text() );

    m_starterDialog.setRiderBib ( sValue );

    //  "Position" is Minute Offset from Race Start
/*
    m_iCurrentPosition = ui->startTimes->item( m_iCurrentRider, 4 )->text().toInt();

    m_dCurrentCountdown = (double)m_startTime.msecsTo( m_startTime.addSecs( m_iCurrentPosition * 60 ) ) / 1000.0;
*/
    m_dCurrentPosition = ui->startTimes->item( m_iCurrentRider, 4 )->text().toFloat();

    m_dCurrentCountdown = (double)m_startTime.msecsTo( m_startTime.addSecs( m_dCurrentPosition * 60 * 1000 ) ) / 1000.0;

    ui->countdown->setText( QString::number( m_dCurrentCountdown ) );

    //  Rider On Deck
    if ( ( m_iCurrentRider + 1 ) < ui->startTimes->rowCount() )
    {
        sValue.sprintf( "%s %s",
                        qPrintable( ui->startTimes->item( m_iCurrentRider + 1, 2 )->text() ),
                        qPrintable( ui->startTimes->item( m_iCurrentRider + 1, 1 )->text() ) );

        ui->riderOnDeck->setText( sValue );

    }
    else
    {
        ui->riderOnDeck->clear();
    }

    //  Rider In the Hole
    if ( ( m_iCurrentRider + 2 ) < ui->startTimes->rowCount() )
    {
        sValue.sprintf( "%s %s",
                        qPrintable( ui->startTimes->item( m_iCurrentRider + 2, 2 )->text() ),
                        qPrintable( ui->startTimes->item( m_iCurrentRider + 2, 1 )->text() ) );

        ui->riderInTheHole->setText( sValue );

    }
    else
    {
        ui->riderInTheHole->clear();
    }

}

void MainWindow::stopTimer( void )
{
    QMessageBox::StandardButton resBtn = QMessageBox::question( this, "Stop Race Timer?",
                                                                    tr("Are you sure?\n"),
                                                                    QMessageBox::No | QMessageBox::Yes,
                                                                    QMessageBox::No );

    if (resBtn == QMessageBox::Yes)
    {
        m_timer->stop();

        resBtn = QMessageBox::question( this, "Reset TT Scoring Application?",
                                        tr("Are you sure?\n"),
                                        QMessageBox::No | QMessageBox::Yes,
                                        QMessageBox::No );

        if ( resBtn == QMessageBox::Yes)
        {
            ui->startTime->setText  ( "--:--:--.---" );
            ui->elapsedTime->setText( "--:--:--.---" );

            ui->startTimer->setEnabled( true  );
            ui->stopTimer->setEnabled ( false );

            //  Clear the "Finish Time" & "Result" from the Start List Table
            for ( int i = 0; i < ui->startTimes->rowCount(); i++ )
            {
                //  Finish Time
                QTableWidgetItem *finishItem = new QTableWidgetItem( "--:--:--.---" );

                finishItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                finishItem->setFlags( finishItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( i, 5, finishItem);

                //  Result
                QTableWidgetItem *resultItem = new QTableWidgetItem( "--:--:--.---" );

                resultItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                resultItem->setFlags( resultItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( i, 6, resultItem);

            }   //  for ( int i = 0; i < ui->startTimes->rowCount(); i++ )

            //  Starting Riders
            ui->riderOnTheRamp->clear();        ui->countdown->clear();
            ui->riderOnDeck->clear();
            ui->riderInTheHole->clear();

            //  Finishing Riders
            ui->latestFinisher_01->clear();     ui->latestTime_01->clear();
            ui->latestFinisher_02->clear();     ui->latestTime_02->clear();
            ui->latestFinisher_03->clear();     ui->latestTime_03->clear();

            ui->finishTimes->clearContents();
            ui->finishTimes->setRowCount( 0 );

            updateResults();
        }

    }   //  if (resBtn != QMessageBox::Yes)

}

void MainWindow::addRider( void )
{
    QString     sText;
    QString     sBibNumber;
    QString     sLastName;
    QString     sFirstName;
    QString     sCategory;
    int         iStartPosition;

    int         iRow = 0;
    int         cRows = ui->startTimes->rowCount();

    m_addRiderDlg.setBibNumber( "" );
    m_addRiderDlg.setLastName( "" );
    m_addRiderDlg.setFirstName("" );
    m_addRiderDlg.setCategory( "Mercyx - Men" );
    m_addRiderDlg.setPosition( 0 );

    if ( m_addRiderDlg.exec() == QDialog::Accepted )
    {
        sBibNumber     = m_addRiderDlg.bibNumber();
        sLastName      = m_addRiderDlg.lastName();
        sFirstName     = m_addRiderDlg.firstName();
        sCategory      = m_addRiderDlg.category();
        iStartPosition = m_addRiderDlg.startPosition();

        //  Determine Appropriate Row for new rider
        iRow = getInsertRow( iStartPosition );

        ui->startTimes->insertRow( iRow );

        //  Bib Item
        QTableWidgetItem *bibItem = new QTableWidgetItem( sBibNumber);

        bibItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        bibItem->setFlags( bibItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 0, bibItem);

        //  Last Name
        QTableWidgetItem *lastNameItem = new QTableWidgetItem( sLastName );

        lastNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        lastNameItem->setFlags( lastNameItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 1, lastNameItem);

        //  First Name
        QTableWidgetItem *firstNameItem = new QTableWidgetItem( sFirstName );

        firstNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        firstNameItem->setFlags( firstNameItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 2, firstNameItem);

        //  Category
        QTableWidgetItem *categoryItem = new QTableWidgetItem( sCategory);

        categoryItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        categoryItem->setFlags( categoryItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 3, categoryItem);

        //  Start Position (Time)
        QTableWidgetItem *startItem = new QTableWidgetItem( QString::number( iStartPosition ) );

        startItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        startItem->setFlags( startItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 4, startItem);

        //  Finish Time
        QTableWidgetItem *finishItem = new QTableWidgetItem( "--:--:--.---" );

        finishItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        finishItem->setFlags( finishItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 5, finishItem);

        //  Result
        QTableWidgetItem *resultItem = new QTableWidgetItem( "--:--:--.---" );

        resultItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
        resultItem->setFlags( resultItem->flags() & ~Qt::ItemIsEditable );

        ui->startTimes->setItem( iRow, 6, resultItem);

    }
}

void MainWindow::editRider   ( void )
{
    QString     sBibNumber;
    QString     sLastName;
    QString     sFirstName;
    QString     sCategory;
    int         iStartPosition; //  It's important to check the starting and ending value of the "start position"
    int         iPosition;      //  Changes in this value will alter the order of the start list table!

    QModelIndexList indexes = ui->startTimes->selectionModel()->selectedRows();

    QModelIndex index = indexes.at(0);

    sBibNumber     = ui->startTimes->item( index.row(), 0 )->text();
    sLastName      = ui->startTimes->item( index.row(), 1 )->text();
    sFirstName     = ui->startTimes->item( index.row(), 2 )->text();
    sCategory      = ui->startTimes->item( index.row(), 3 )->text();
    iStartPosition = ui->startTimes->item( index.row(), 4 )->text().toInt();

    m_addRiderDlg.setBibNumber( sBibNumber );
    m_addRiderDlg.setLastName ( sLastName );
    m_addRiderDlg.setFirstName( sFirstName );
    m_addRiderDlg.setCategory ( sCategory );
    m_addRiderDlg.setPosition ( iStartPosition );

    if ( m_addRiderDlg.exec() == QDialog::Accepted )
    {
        sBibNumber     = m_addRiderDlg.bibNumber();
        sLastName      = m_addRiderDlg.lastName();
        sFirstName     = m_addRiderDlg.firstName();
        sCategory      = m_addRiderDlg.category();

        iPosition      = m_addRiderDlg.startPosition();     //  Get the "Start Position"

        if ( iPosition == iStartPosition )
        {
            //  Update Start List Table
            ui->startTimes->item( index.row(), 0 )->setText( sBibNumber );
            ui->startTimes->item( index.row(), 1 )->setText( sLastName  );
            ui->startTimes->item( index.row(), 2 )->setText( sFirstName );
            ui->startTimes->item( index.row(), 3 )->setText( sCategory  );
        }
        else
        {
            //  Remove Existing Rider Entry and "Re-Insert" into Start List
            ui->startTimes->removeRow( index.row() );

            //  Determine Appropriate Row for new rider
            int iRow = getInsertRow( iPosition );

            ui->startTimes->insertRow( iRow );

            //  Bib Item
            QTableWidgetItem *bibItem = new QTableWidgetItem( sBibNumber);

            bibItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            bibItem->setFlags( bibItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 0, bibItem);

            //  Last Name
            QTableWidgetItem *lastNameItem = new QTableWidgetItem( sLastName );

            lastNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            lastNameItem->setFlags( lastNameItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 1, lastNameItem);

            //  First Name
            QTableWidgetItem *firstNameItem = new QTableWidgetItem( sFirstName );

            firstNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            firstNameItem->setFlags( firstNameItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 2, firstNameItem);

            //  Category
            QTableWidgetItem *categoryItem = new QTableWidgetItem( sCategory);

            categoryItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            categoryItem->setFlags( categoryItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 3, categoryItem);

            //  Start Position (Time)
            QTableWidgetItem *startItem = new QTableWidgetItem( QString::number( iPosition ) );

            startItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            startItem->setFlags( startItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 4, startItem);

            //  Finish Time
            QTableWidgetItem *finishItem = new QTableWidgetItem( "--:--:--.---" );

            finishItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            finishItem->setFlags( finishItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 5, finishItem);

            //  Result
            QTableWidgetItem *resultItem = new QTableWidgetItem( "--:--:--.---" );

            resultItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
            resultItem->setFlags( resultItem->flags() & ~Qt::ItemIsEditable );

            ui->startTimes->setItem( iRow, 6, resultItem);

        }   //  if ( iPosition == iStartPosition )

    }   //  if ( m_addRiderDlg.exec() == QDialog::Accepted )

}

void MainWindow::removeRider( void )
{
    QList<int>      iRows;
    int             iRow;

    QModelIndexList indexes = ui->startTimes->selectionModel()->selectedRows();

    for ( int i = 0; i < indexes.count(); i++ )
    {
        iRow = indexes.at(i).row();

        iRows.append( iRow );

    }   //  for ( int i = 0; i < indexes.count(); i++ )

    qSort( iRows );

    for ( int i = iRows.count() - 1; i >= 0; i-- )
    {
        //  Physically Remove Rows
//      ui->startTimes->removeRow( iRows.at(i) );

        if ( ( ui->startTimes->item( iRows.at(i), 5 )->text() == "--:--:--.---" ) &&
             ( ui->startTimes->item( iRows.at(i), 6 )->text() == "--:--:--.---" ) )
        {
            ui->startTimes->item( iRows.at(i), 0 )->setText( "----" );
            ui->startTimes->item( iRows.at(i), 1 )->setText( "----" );
            ui->startTimes->item( iRows.at(i), 2 )->setText( "----" );
            ui->startTimes->item( iRows.at(i), 3 )->setText( "----" );
        }
    }   //  for ( int i = Rows.count() - 1; i >= 0; i-- )

}

void MainWindow::recordFinish( void )
{
    QString     sBibNumber;
    QString     sLastName;
    QString     sFirstName;
    QString     sCategory;
    QDateTime   finishTime = QDateTime::currentDateTime();
    QString     sFinish;
    QString     sResult;

    int         iRow = ui->finishTimes->rowCount();

    qDebug( "Finish Time: %s", qPrintable( finishTime.toString( "hh:mm:ss.zzz" ) ) );

    //  Add Record to Finish Table
    ui->finishTimes->insertRow( iRow );

    //  Bib Item
    QTableWidgetItem *bibItem = new QTableWidgetItem( sBibNumber);

    bibItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
//  bibItem->setFlags( bibItem->flags() & ~Qt::ItemIsEditable );

    ui->finishTimes->setItem( iRow, 0, bibItem);

    //  Last Name
    QTableWidgetItem *lastNameItem = new QTableWidgetItem( sLastName );

    lastNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
    lastNameItem->setFlags( lastNameItem->flags() & ~Qt::ItemIsEditable );

    ui->finishTimes->setItem( iRow, 1, lastNameItem);

    //  First Name
    QTableWidgetItem *firstNameItem = new QTableWidgetItem( sFirstName );

    firstNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
    firstNameItem->setFlags( firstNameItem->flags() & ~Qt::ItemIsEditable );

    ui->finishTimes->setItem( iRow, 2, firstNameItem);

    //  Category
    QTableWidgetItem *categoryItem = new QTableWidgetItem( sCategory );

    categoryItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
    categoryItem->setFlags( categoryItem->flags() & ~Qt::ItemIsEditable );

    ui->finishTimes->setItem( iRow, 3, categoryItem);

    //  Finish Time
    sFinish.sprintf( "%s", qPrintable( finishTime.toString( "hh:mm:ss.zzz" ) ) );

    QTableWidgetItem *finishItem = new QTableWidgetItem( sFinish );

    finishItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
    finishItem->setFlags( finishItem->flags() & ~Qt::ItemIsEditable );

    ui->finishTimes->setItem( iRow, 4, finishItem);

    //  Result;
    QTableWidgetItem *resultItem = new QTableWidgetItem( sResult );

    resultItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
    resultItem->setFlags( resultItem->flags() & ~Qt::ItemIsEditable );

    ui->finishTimes->setItem( iRow, 5, resultItem);
}

void MainWindow::editStartTime()
{
    DateTimeDlg     startTime;

    if ( m_startTime.isNull() )
        m_startTime = QDateTime::currentDateTime();

    startTime.setDateTime( m_startTime );

    if ( startTime.exec() == QDialog::Accepted )
    {
        m_startTime = startTime.dateTime();

        ui->startTime->setText( m_startTime.toString( "hh:mm:ss.zzz" ) );
    }

}

void MainWindow::raceTimeout()
{
    m_currentTime = QDateTime::currentDateTime();

    QString     sValue;
    QString     sTime;

    QDateTime   elapsedTime = m_currentTime;
    elapsedTime.setTime( QTime(0,0,0,0) );

    qint64  elapsed = m_startTime.msecsTo( m_currentTime );

    //  Race Time to Display on Starter Dialog
    QTime   raceTime    = QTime(18,0,0,0).addMSecs( elapsed );

    elapsedTime = elapsedTime.addMSecs( elapsed );
    sTime.sprintf( "%s", qPrintable( elapsedTime.toString( "hh:mm:ss.zzz" ) ) );

    ui->elapsedTime->setText( sTime );

    m_starterDialog.setRaceTime( raceTime );

//  m_dCurrentCountdown = (double)m_currentTime.msecsTo( m_startTime.addSecs( m_iCurrentPosition * 60 ) ) / 1000.0;

    m_dCurrentCountdown = (double)m_currentTime.msecsTo( m_startTime.addMSecs( m_dCurrentPosition * 60 * 1000 ) ) / 1000.0;

    if ( m_dCurrentCountdown <= 16.0 && m_bPlay )
    {
/*
        QMediaPlayer *player;

        player = new QMediaPlayer;

        player->setMedia( QUrl::fromLocalFile("start.mp3" ) );
        player->setVolume( 50 );
        player->play();
*/
        m_bPlay = false;

        if ( m_player->mediaStatus()== QMediaPlayer::LoadedMedia )
        {
//          m_player->setPosition(0);
//          m_player->play();

            QApplication::processEvents( QEventLoop::ExcludeUserInputEvents );

            qDebug( "Play! ( %.1f )", m_dCurrentCountdown );

        }
        else
        {
            qDebug( "Not Loaded" );
        }
    }

    if ( m_dCurrentCountdown >= 0.0 )
    {
        ui->countdown->setText( QString::number( m_dCurrentCountdown, 'f', 0 ) );

        m_starterDialog.updateCounter( QString::number( m_dCurrentCountdown, 'f', 0 ) );
    }
    else
    {
        //  Reset Boolean to Play "Start" MP3
        m_bPlay = true;

        QString     sFile = QApplication::applicationDirPath() + "/start.mp3";

        m_player->setMedia(QUrl::fromLocalFile(QFileInfo(sFile).absoluteFilePath()));

        m_iCurrentRider++;      //  Increment to Next Rider in Start List

        if ( m_iCurrentRider < ui->startTimes->rowCount() )
        {
            //  Set Rider on the Ramp
            sValue.sprintf( "%s %s",
                            qPrintable( ui->startTimes->item( m_iCurrentRider, 2 )->text() ),
                            qPrintable( ui->startTimes->item( m_iCurrentRider, 1 )->text() ) );

            ui->riderOnTheRamp->setText( sValue );


            //  "Position" is Minute Offset from Race Start
/*
            m_iCurrentPosition = ui->startTimes->item( m_iCurrentRider, 4 )->text().toInt();

            m_dCurrentCountdown = (double)m_currentTime.msecsTo( m_startTime.addSecs( m_iCurrentPosition * 60 ) ) / 1000.0;
*/
            m_dCurrentPosition = ui->startTimes->item( m_iCurrentRider, 4 )->text().toFloat();

            m_dCurrentCountdown = (double)m_currentTime.msecsTo( m_startTime.addSecs( m_dCurrentPosition * 60 ) ) / 1000.0;

            ui->countdown->setText( QString::number( m_dCurrentCountdown, 'f', 0 ) );

            m_starterDialog.updateCounter( QString::number( m_dCurrentCountdown, 'f', 0 ) );

            //  Update Starter Dialog
            m_starterDialog.setOnTheLine( sValue );

            //  Bib # of Rider on the Ramp
            sValue = QString( "# %1" ).arg(ui->startTimes->item( m_iCurrentRider, 0 )->text() );

            m_starterDialog.setRiderBib ( sValue );

            //  Rider On Deck
            if ( ( m_iCurrentRider + 1 ) < ui->startTimes->rowCount() )
            {
                sValue.sprintf( "%s %s",
                                qPrintable( ui->startTimes->item( m_iCurrentRider + 1, 2 )->text() ),
                                qPrintable( ui->startTimes->item( m_iCurrentRider + 1, 1 )->text() ) );

                ui->riderOnDeck->setText( sValue );

                m_starterDialog.setNextRider( sValue );

            }
            else
            {
                ui->riderOnDeck->clear();

                m_starterDialog.setNextRider( QString() );
            }

            //  Rider In the Hole
            if ( ( m_iCurrentRider + 2 ) < ui->startTimes->rowCount() )
            {
                sValue.sprintf( "%s %s",
                                qPrintable( ui->startTimes->item( m_iCurrentRider + 2, 2 )->text() ),
                                qPrintable( ui->startTimes->item( m_iCurrentRider + 2, 1 )->text() ) );

                ui->riderInTheHole->setText( sValue );

            }
            else
            {
                ui->riderInTheHole->clear();
            }

        }
        else
        {
            //  Hold at Last Record
            m_iCurrentRider = ui->startTimes->rowCount() - 1;

            ui->riderOnTheRamp->clear();
            ui->countdown->clear();

            m_starterDialog.setOnTheLine ( QString() );
            m_starterDialog.updateCounter( QString() );

        }   //  if ( m_iCurrentRider < ui->startTimes->rowCount() )

    }
}

void MainWindow::finishCellClicked( int row, int col )
{
    QString         sFinish;

    DateTimeDlg     finishEdit;

    QString     sBibNumber;
    QString     sLast;
    QString     sFirst;
    QString     sCategory;
    QString     sFinishTime;
    QString     sResult;

    QDateTime   startTime;
    QDateTime   finishTime;
    QDateTime   result;

    int         iStartIndex;
    int         iStartPosition;
    double      dStartPosition;

    bool        bFound = false;


    //  Process 'Click' in Finish Time Cells Only
    if ( col == 4 )
    {
        if ( m_startTime.isNull() )
            m_startTime = QDateTime::currentDateTime();

        sFinish    = ui->finishTimes->item( row, col )->text();

        finishTime = m_startTime;
        finishTime.setTime( QTime::fromString( sFinish, "hh:mm:ss.zzz" ) );

        qDebug( "%s", qPrintable( finishTime.toString( "MM/dd/yyyy hh:mm:ss.zzz" ) ) );

        finishEdit.setDateTime( finishTime );

        if ( finishEdit.exec() == QDialog::Accepted )
        {
            finishTime = finishEdit.dateTime();

            ui->finishTimes->item( row, col )->setText( finishTime.toString( "hh:mm:ss.zzz" ) );

            //  Check Bib # and update finish time record & start time record
            if ( !ui->finishTimes->item( row, 0 )->text().isEmpty() )
            {
                sBibNumber = ui->finishTimes->item( row, 0 )->text();

                //  Find the bib # in the "Start List"
                for ( int i = 0; ( i < ui->startTimes->rowCount() ) && !bFound; i++ )
                {
                    if ( sBibNumber == ui->startTimes->item( i, 0 )->text() )
                    {
                        iStartIndex = i;
                        bFound      = true;
                    }

                }   //  for ( int i = 0; ( i < ui->finishTimes->rowCount() ) && !bFound; i++ )

                if ( bFound )
                {
                    //  Extract Data from Start List
                    sLast          = ui->startTimes->item ( iStartIndex, 1 )->text();
                    sFirst         = ui->startTimes->item ( iStartIndex, 2 )->text();
                    sCategory      = ui->startTimes->item ( iStartIndex, 3 )->text();
                    iStartPosition = ui->startTimes->item ( iStartIndex, 4 )->text().toInt();
                    dStartPosition = ui->startTimes->item ( iStartIndex, 4 )->text().toFloat();

                    //  Extract Finish Time from Finish List
                    sFinishTime    = ui->finishTimes->item( row, 4 )->text();

                    //  Populate Finish List for Specified Bib #
                    ui->finishTimes->item( row, 1 )->setText( sLast  );
                    ui->finishTimes->item( row, 2 )->setText( sFirst );
                    ui->finishTimes->item( row, 3 )->setText( sCategory );

                    //  Calculate Result
                    finishTime = m_startTime;
                    finishTime.setTime( QTime::fromString( sFinishTime, "hh:mm:ss.zzz" ) );

                    qDebug( "finish : %s (%s)", qPrintable( finishTime.toString( "hh:mm:ss.zzz" ) ), qPrintable( sFinishTime ) );

//                  startTime = m_startTime.addSecs( iStartPosition * 60 );
                    startTime = m_startTime.addMSecs( dStartPosition * 60 * 1000 );

                    qDebug( "start : %s", qPrintable( startTime.toString( "hh:mm:ss.zzz" ) ) );

                    qint64  elapsed = startTime.msecsTo( finishTime );

                    qDebug( "elapsed : %d", elapsed );

                    //  Initialize Result Variable
                    result = m_startTime;
                    result.setTime( QTime( 0,0,0,0 ) );

                    result = result.addMSecs( elapsed );

                    sResult.sprintf( "%s", qPrintable( result.toString( "hh:mm:ss.zzz" ) ) );

                    //  Record 'Result Time' in Finish Times Table
                    ui->finishTimes->item( row, 5 )->setText( sResult );

                    //  Record 'Finish Time' & 'Result Time' in Start List Table
                    ui->startTimes->item( iStartIndex, 5 )->setText( sFinishTime );
                    ui->startTimes->item( iStartIndex, 6 )->setText( sResult     );

                    //  Update the "Results"
                    updateResults();
                }
                else
                {
                    //  Populate Finish List for Specified Bib #
                    ui->finishTimes->item( row, 1 )->setText( "" );
                    ui->finishTimes->item( row, 2 )->setText( "" );
                    ui->finishTimes->item( row, 3 )->setText( "" );
                    ui->finishTimes->item( row, 5 )->setText( "" );

                    //  Correct "Scoring" on Start List
                    //      Finish Table contains a bib # that is not found in Start List
                    //      Check Scoring in case a bib # is no longer associated with a "Finish Time"
                    correctScoring();

                    //  Update the "Results"
                    updateResults();
                }

            }   //  if ( ( col == 0 ) && ( !ui->finishTimes->item( row, 0 )->text().isEmpty() ) )

        }

    }   //  if ( col == 4 )
}

void MainWindow::finishCellChanged(int row, int col )
{
    qDebug( "finishCellChanged( %d, %d )", row, col );

    QString     sBibNumber;
    QString     sLast;
    QString     sFirst;
    QString     sCategory;
    QString     sFinishTime;
    QString     sResult;

    QDateTime   startTime;
    QDateTime   finishTime;
    QDateTime   result;

    int         iStartIndex;
    int         iStartPosition;
    double      dStartPosition;

    bool        bFound = false;

    if ( ( col == 0 ) && ( !ui->finishTimes->item( row, 0 )->text().isEmpty() ) )
    {
        sBibNumber = ui->finishTimes->item( row, 0 )->text();

        //  Find the bib # in the "Start List"
        for ( int i = 0; ( i < ui->startTimes->rowCount() ) && !bFound; i++ )
        {
            if ( sBibNumber == ui->startTimes->item( i, 0 )->text() )
            {
                iStartIndex = i;
                bFound      = true;
            }

        }   //  for ( int i = 0; ( i < ui->finishTimes->rowCount() ) && !bFound; i++ )

        if ( bFound )
        {
            //  Extract Data from Start List
            sLast          = ui->startTimes->item ( iStartIndex, 1 )->text();
            sFirst         = ui->startTimes->item ( iStartIndex, 2 )->text();
            sCategory      = ui->startTimes->item ( iStartIndex, 3 )->text();
            iStartPosition = ui->startTimes->item ( iStartIndex, 4 )->text().toInt();
            dStartPosition = ui->startTimes->item ( iStartIndex, 4 )->text().toDouble();    //  30 second increments on start

            //  Extract Finish Time from Finish List
            sFinishTime    = ui->finishTimes->item( row, 4 )->text();

            //  Populate Finish List for Specified Bib #
            ui->finishTimes->item( row, 1 )->setText( sLast  );
            ui->finishTimes->item( row, 2 )->setText( sFirst );
            ui->finishTimes->item( row, 3 )->setText( sCategory );

            //  Calculate Result
            finishTime = m_startTime;
            finishTime.setTime( QTime::fromString( sFinishTime, "hh:mm:ss.zzz" ) );

            qDebug( "finish : %s (%s)", qPrintable( finishTime.toString( "hh:mm:ss.zzz" ) ), qPrintable( sFinishTime ) );

//          startTime = m_startTime.addSecs( iStartPosition * 60 );             //  Int    Start Position - 60 second intervals
            startTime = m_startTime.addMSecs( dStartPosition * 60 * 1000 );     //  double Start Position - 30 second intervals

            qDebug( "start : %s", qPrintable( startTime.toString( "hh:mm:ss.zzz" ) ) );

            qint64  elapsed = startTime.msecsTo( finishTime );

            qDebug( "elapsed : %d", elapsed );

            //  Initialize Result Variable
            result = m_startTime;
            result.setTime( QTime( 0,0,0,0 ) );

            result = result.addMSecs( elapsed );

            sResult.sprintf( "%s", qPrintable( result.toString( "hh:mm:ss.zzz" ) ) );

            //  Record 'Result Time' in Finish Times Table
            ui->finishTimes->item( row, 5 )->setText( sResult );

            //  Record 'Finish Time' & 'Result Time' in Start List Table
            ui->startTimes->item( iStartIndex, 5 )->setText( sFinishTime );
            ui->startTimes->item( iStartIndex, 6 )->setText( sResult     );

            //  Update the "Results"
            updateResults();
        }
        else
        {
            //  Populate Finish List for Specified Bib #
            ui->finishTimes->item( row, 1 )->setText( "" );
            ui->finishTimes->item( row, 2 )->setText( "" );
            ui->finishTimes->item( row, 3 )->setText( "" );
            ui->finishTimes->item( row, 5 )->setText( "" );

            //  Correct "Scoring" on Start List
            //      Finish Table contains a bib # that is not found in Start List
            //      Check Scoring in case a bib # is no longer associated with a "Finish Time"
            correctScoring();

            //  Update the "Results"
            updateResults();
        }

    }   //  if ( ( col == 0 ) && ( !ui->finishTimes->item( row, 0 )->text().isEmpty() ) )

}

void MainWindow::correctScoring( void )
{
    QString     sBib;
    QString     sFinish;
    QString     sResult;

    //  Process Start List and "Verify" that a valid "Finish Time" exists for Each Bib #
    //  Reset the "Finish Time" and "Result" if a bib # match is not found in the Finish Times
    for ( int iStart = 0; iStart < ui->startTimes->rowCount(); iStart++ )
    {
        bool    bFound = false;

        sBib = ui->startTimes->item( iStart, 0 )->text();

        for ( int iFinish = 0; ( iFinish < ui->finishTimes->rowCount() ) && !bFound; iFinish++ )
        {
            if ( sBib == ui->finishTimes->item( iFinish, 0 )->text() )
            {
                bFound = true;

                sFinish = ui->finishTimes->item( iFinish, 4 )->text();
                sResult = ui->finishTimes->item( iFinish, 5 )->text();
            }

        }   //  for ( int iFinish = 0; ( iFinish < ui->finishTimes->rowCount() ) && !bFound; iFinish++ )

        if ( bFound )
        {
            ui->startTimes->item( iStart, 5 )->setText( sFinish );
            ui->startTimes->item( iStart, 6 )->setText( sResult );
        }
        else
        {
            ui->startTimes->item( iStart, 5 )->setText( "--:--:--.---" );
            ui->startTimes->item( iStart, 6 )->setText( "--:--:--.---" );
        }

    }   //  for ( int iStart = 0; iStart < ui->startTimes->rowCount(); iStart++ )
}

void MainWindow::updateResults( void )
{
    QString         sBuffer;

    QStringList     sCategoryResults;
    QStringList     sOverallResults;

    QString         sHTML;

    for ( int i = 0; i < ui->startTimes->rowCount(); i++ )
    {
        QString     sCategory = ui->startTimes->item( i, 3 )->text();
        QString     sResult   = ui->startTimes->item( i, 6 )->text();
        QString     sBib      = ui->startTimes->item( i, 0 )->text();
        QString     sFirst    = ui->startTimes->item( i, 2 )->text();
        QString     sLast     = ui->startTimes->item( i, 1 )->text();

        QString     sName;

        sName.sprintf( "%s %s", qPrintable( sFirst ), qPrintable( sLast ) );

        //  Overall Results
        if ( sResult != "--:--:--.---" )
        {
            if ( ( sCategory != "10-14 (M)" ) && ( sCategory != "15-18 (M)" ) &&
                 ( sCategory != "10-14 (F)" ) && ( sCategory != "15-18 (F)" ) )
            {
                //  Exclude "Juniors" from Overall Results
                sBuffer.sprintf( "%s  %-24s  %-18s", qPrintable( sResult.mid(0,10) ), qPrintable( sName ), qPrintable( sCategory ) );

                sOverallResults.append( sBuffer );
            }

        }   //  if ( sResult != "--:--:--.---" )

        //  Category Results
        if ( sResult != "--:--:--.---" )
        {
            sBuffer.sprintf( "%-18s  %s  %-24s", qPrintable( sCategory ), qPrintable( sResult.mid(0,10) ), qPrintable( sName ) );

            sCategoryResults.append( sBuffer );

        }   //  if ( sResult != "--:--:--.---" )

    }   //  for ( int i = 0; i < ui->startTimes->rowCount(); i++ )

    qSort( sOverallResults  );
    qSort( sCategoryResults );

    sHTML += "<html><body>\n";

    sHTML += "<h2>Category Results</h2>\n";

    sHTML += "<pre>\n";

    //  Process Category Results;
    QString sPrevious = "";
    for ( int i = 0; i < sCategoryResults.count(); i++ )
    {
        sBuffer.sprintf( "%s\n", qPrintable( sCategoryResults.at(i) ) );

        if ( sPrevious.mid(0,15) != sBuffer.mid(0,15) )
        {
            sHTML += "\n";
        }

        sHTML += sBuffer;

        //  Save and Compare
        sPrevious = sBuffer;
    }

    sHTML += "</pre>\n";

    sHTML += "<p>\n";
    sHTML += "<h2>Overall Results</h2>\n";
    sHTML += "<pre>\n";

    //  Process Overall Results
    for ( int i = 0; i < sOverallResults.count(); i++ )
    {
        sBuffer.sprintf( "%3d)  %s\n", ( i + 1 ), qPrintable( sOverallResults.at(i) ) );

        sHTML += sBuffer;
    }

    sHTML += "</pre>\n";
    sHTML += "</body></html>\n";

    //  Update Results 'Tab' of Main Window
    ui->resultsBrowser->setHtml( sHTML );

    //  Update Results in "Results Dialog"
    m_resultsDialog.setFromHtml( sHTML, false );
    m_resultsDialog.show();
    m_resultsDialog.raise();
}

void MainWindow::importStartList( void )
{
    qDebug( "importStartList()" );

    QString     sHeader;
    QString     sRecord;

    QString     sBib;
    QString     sLast;
    QString     sFirst;
    QString     sCategory;
    QString     sPosition;
    QString     sFinish;
    QString     sResult;

    QString     fileName = QFileDialog::getOpenFileName(this, tr("Open TT Start List"), "tt-start-list.csv", tr("TT Start List (*.csv)") );

    QFile       file( fileName );

    if ( file.open( QIODevice::ReadOnly ) )
    {
        QTextStream in(&file);

        ui->startTimes->clearContents();
        ui->startTimes->setRowCount(0);

        sHeader = in.readLine();

        while ( !in.atEnd() )
        {
            sRecord = in.readLine();

            //	Trim <CR><LF> from Input Record - trimmed() will remove white space from beginning and end
            sRecord = sRecord.remove( '\n' );
            sRecord = sRecord.remove( '\r' );

            QStringList cols = sRecord.split(',');

            if ( cols.count() == 7 )
            {
                qDebug( "%s", qPrintable( sRecord ) );

                sBib        = cols.at(0).trimmed();
                sLast       = cols.at(1).trimmed();
                sFirst      = cols.at(2).trimmed();
                sCategory   = cols.at(3).trimmed();
                sPosition   = cols.at(4).trimmed();
                sFinish     = cols.at(5).trimmed();
                sResult     = cols.at(6).trimmed();

                int     iRow = ui->startTimes->rowCount();

                ui->startTimes->insertRow( iRow );

                //  Bib Item
                QTableWidgetItem *bibItem = new QTableWidgetItem( sBib );

                bibItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                bibItem->setFlags( bibItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 0, bibItem);

                //  Last Name
                QTableWidgetItem *lastNameItem = new QTableWidgetItem( sLast );

                lastNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                lastNameItem->setFlags( lastNameItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 1, lastNameItem);

                //  First Name
                QTableWidgetItem *firstNameItem = new QTableWidgetItem( sFirst );

                firstNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                firstNameItem->setFlags( firstNameItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 2, firstNameItem);

                //  Category
                QTableWidgetItem *categoryItem = new QTableWidgetItem( sCategory);

                categoryItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                categoryItem->setFlags( categoryItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 3, categoryItem);

                //  Start Position (Time)
                QTableWidgetItem *startItem = new QTableWidgetItem( sPosition );

                startItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                startItem->setFlags( startItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 4, startItem);

                //  Finish Time
                QTableWidgetItem *finishItem = new QTableWidgetItem( sFinish );

                finishItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                finishItem->setFlags( finishItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 5, finishItem);

                //  Result
                QTableWidgetItem *resultItem = new QTableWidgetItem( sResult );

                resultItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                resultItem->setFlags( resultItem->flags() & ~Qt::ItemIsEditable );

                ui->startTimes->setItem( iRow, 6, resultItem);

            }   //  if ( cols.count() == 7 )

        }   //  while ( !in.atEnd() )

    }   //  if ( file.open( QIODevice::ReadOnly ) )
}

void MainWindow::exportStartList( void )
{
    qDebug( "exportStartList()" );

    QString     sBuffer;
    QString     sFile;

    sFile = "tt-start-list.csv";

    QString filePath = QFileDialog::getSaveFileName(this, tr ( "Export StartList" ),  sFile, tr ("CSV (*.csv)" ));

    if ( !filePath.isEmpty() )
    {
        QFile file(filePath);

        if ( file.open( QFile::WriteOnly ) )
        {
            QTextStream stream( &file );

            stream << "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT\r\n";

            for ( int i = 0; i < ui->startTimes->rowCount(); i++ )
            {
                QString sBib        = ui->startTimes->item( i, 0 )->text();
                QString sLast       = ui->startTimes->item( i, 1 )->text();
                QString sFirst      = ui->startTimes->item( i, 2 )->text();
                QString sCategory   = ui->startTimes->item( i, 3 )->text();
                QString sPosition   = ui->startTimes->item( i, 4 )->text();
                QString sFinish     = ui->startTimes->item( i, 5 )->text();
                QString sResult     = ui->startTimes->item( i, 6 )->text();

                sBuffer.sprintf( "%s,%s,%s,%s,%s,%s,%s\r\n",
                                 qPrintable( sBib ),
                                 qPrintable( sLast ),
                                 qPrintable( sFirst ),
                                 qPrintable( sCategory ),
                                 qPrintable( sPosition ),
                                 qPrintable( sFinish ),
                                 qPrintable ( sResult ) );

                stream << sBuffer;

            }   //  for ( int i = 0; i < ui->startTimes->rowCount(); i++ )

            file.close();

        }   //  if ( file.open( QFile::WriteOnly ) )

    }   //  if ( !filePath.isEmpty() )

}

void MainWindow::importFinishList( void )
{
    QString     sHeader;
    QString     sRecord;

    QString     sBib;
    QString     sLast;
    QString     sFirst;
    QString     sCategory;
    QString     sFinish;
    QString     sResult;

    QString     fileName = QFileDialog::getOpenFileName(this, tr("Open TT Finish List"), "tt-finish-list.csv", tr("TT Finish List (*.csv)") );

    QFile       file( fileName );

    if ( file.open( QIODevice::ReadOnly ) )
    {
//      disconnect( ui->finishTimes, SIGNAL(cellChanged(int,int) ), this, SLOT(finishCellChanged(int,int) ) );

        ui->finishTimes->blockSignals( true );

        QTextStream in(&file);

        ui->finishTimes->clearContents();
        ui->finishTimes->setRowCount(0);

        sHeader = in.readLine();

        while ( !in.atEnd() )
        {
            sRecord = in.readLine();

            //	Trim <CR><LF> from Input Record - trimmed() will remove white space from beginning and end
            sRecord = sRecord.remove( '\n' );
            sRecord = sRecord.remove( '\r' );

            QStringList cols = sRecord.split(',');

            if ( cols.count() == 6 )
            {
                qDebug( "%s", qPrintable( sRecord ) );

                sBib        = cols.at(0).trimmed();
                sLast       = cols.at(1).trimmed();
                sFirst      = cols.at(2).trimmed();
                sCategory   = cols.at(3).trimmed();
                sFinish     = cols.at(4).trimmed();

                if ( sFinish.length() < 12 )
                    sFinish = sFinish + "0";

                sResult     = cols.at(5).trimmed();

                int     iRow = ui->finishTimes->rowCount();

                ui->finishTimes->insertRow( iRow );

                //  Bib Item
                QTableWidgetItem *bibItem = new QTableWidgetItem( sBib );

                bibItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
//                bibItem->setFlags( bibItem->flags() & ~Qt::ItemIsEditable );

                ui->finishTimes->setItem( iRow, 0, bibItem);

                //  Last Name
                QTableWidgetItem *lastNameItem = new QTableWidgetItem( sLast );

                lastNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                lastNameItem->setFlags( lastNameItem->flags() & ~Qt::ItemIsEditable );

                ui->finishTimes->setItem( iRow, 1, lastNameItem);

                //  First Name
                QTableWidgetItem *firstNameItem = new QTableWidgetItem( sFirst );

                firstNameItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                firstNameItem->setFlags( firstNameItem->flags() & ~Qt::ItemIsEditable );

                ui->finishTimes->setItem( iRow, 2, firstNameItem);

                //  Category
                QTableWidgetItem *categoryItem = new QTableWidgetItem( sCategory);

                categoryItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                categoryItem->setFlags( categoryItem->flags() & ~Qt::ItemIsEditable );

                ui->finishTimes->setItem( iRow, 3, categoryItem);

                //  Finish Time
                QTableWidgetItem *finishItem = new QTableWidgetItem( sFinish );

                finishItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                finishItem->setFlags( finishItem->flags() & ~Qt::ItemIsEditable );

                ui->finishTimes->setItem( iRow, 4, finishItem);

                //  Result
                QTableWidgetItem *resultItem = new QTableWidgetItem( sResult );

                resultItem->setTextAlignment( Qt::AlignCenter | Qt::AlignVCenter );
                resultItem->setFlags( resultItem->flags() & ~Qt::ItemIsEditable );

                ui->finishTimes->setItem( iRow, 5, resultItem);

            }   //  if ( cols.count() == 6 )

        }   //  while ( !in.atEnd() )

//      connect( ui->finishTimes,SIGNAL(cellChanged(int,int)),SLOT(finishCellChanged(int,int)));

        ui->finishTimes->blockSignals( false );

        //  Fix Results
        correctScoring();

        updateResults();

    }   //  if ( file.open( QIODevice::ReadOnly ) )

}

void MainWindow::exportFinishList( void )
{
    qDebug( "exportFinishList()" );

    QString     sBuffer;
    QString     sFile;

    sFile = "tt-finish-list.csv";

    QString filePath = QFileDialog::getSaveFileName(this, tr ( "Export Finish List" ),  sFile, tr ("CSV (*.csv)" ));

    if ( !filePath.isEmpty() )
    {
        QFile file(filePath);

        if ( file.open( QFile::WriteOnly ) )
        {
            QTextStream stream( &file );

            stream << "BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, FINISH_TIME, RESULT\r\n";

            for ( int i = 0; i < ui->finishTimes->rowCount(); i++ )
            {
                QString sBib        = ui->finishTimes->item( i, 0 )->text();
                QString sLast       = ui->finishTimes->item( i, 1 )->text();
                QString sFirst      = ui->finishTimes->item( i, 2 )->text();
                QString sCategory   = ui->finishTimes->item( i, 3 )->text();
                QString sFinish     = ui->finishTimes->item( i, 4 )->text();
                QString sResult     = ui->finishTimes->item( i, 5 )->text();

                sBuffer.sprintf( "%s,%s,%s,%s,%s,%s\r\n",
                                 qPrintable( sBib ),
                                 qPrintable( sLast ),
                                 qPrintable( sFirst ),
                                 qPrintable( sCategory ),
                                 qPrintable( sFinish ),
                                 qPrintable ( sResult ) );

                stream << sBuffer;

            }   //  for ( int i = 0; i < ui->startTimes->rowCount(); i++ )

            file.close();

        }   //  if ( file.open( QFile::WriteOnly ) )

    }   //  if ( !filePath.isEmpty() )

}

void MainWindow::exportResults( void )
{
    qDebug( "exportResults()" );
}

int MainWindow::getInsertRow( int iStartPosition )
{
    //  Determine Appropriate  'insert' position in Riders table for specified 'Start Time'
    int     iRow      =  0;
    int     iCurrent  = -1;
    int     iPrevious = -1;

    bool    bFound = false;

    for ( int i = 0; i < ui->startTimes->rowCount() & !bFound; i++ )
    {
        iCurrent = ui->startTimes->item(i,4)->text().toInt();

        if ( iStartPosition < iCurrent )
        {
            iRow   = i;
            bFound = true;
        }
        else
        {
            iRow = i+1;
        }

    }

    return iRow;
}

void MainWindow::startListSelectionChanged(QItemSelection current, QItemSelection previous )
{
    QModelIndexList rows = ui->startTimes->selectionModel()->selectedRows();

    //  Only Allow Edit and Delete of Riders before race starts
    if      ( rows.count() == 1 )
    {
        if ( !m_timer->isActive() )
            ui->editRider->setEnabled( true );

        ui->removeRider->setEnabled( true );
    }
    else if ( rows.count() > 1 )
    {
        ui->editRider->setEnabled( false );

        ui->removeRider->setEnabled( true );
    }
    else
    {
        ui->editRider->setEnabled( false );
        ui->removeRider->setEnabled( false );
    }
}

void MainWindow::keyPressEvent( QKeyEvent *event )
{
    if ( event->key() == Qt::Key_T && event->modifiers() == Qt::CTRL )   //  'T' - Record Finish Time
    {
        recordFinish();

    }
    else if ( event->key() == Qt::Key_S && event->modifiers() == Qt::CTRL ) //  'S' - Show Starter Dialog
    {
        m_starterDialog.show();
        m_resultsDialog.show();

    }   //  ( event->key() )

}

void MainWindow::closeEvent( QCloseEvent *event )
{
    QMessageBox::StandardButton resBtn = QMessageBox::question( this, "Exit TT Scoring Application",
                                                                    tr("Are you sure?\n"),
                                                                    QMessageBox::No | QMessageBox::Yes,
                                                                    QMessageBox::No);

    if (resBtn != QMessageBox::Yes) {
        event->ignore();
    } else {
        event->accept();
    }
}

void MainWindow::importSeriesResults( void )
{
    qDebug( "importSeriesResults()" );

    QString     sCurrent;   //  Category
    QString     sHeader;
    QString     sRecord;
    QString     sPoints;
    QString     sCategory;
    QString     sLast;
    QString     sFirst;
    QString     sName;
    QString     sHtml;

    QStringList sTokens;


    QString     fileName = QFileDialog::getOpenFileName(this, tr("Open TT Series Results"), "2018-tt-series-results.csv", tr("TT Series Results (*.csv)") );

    QFile       file( fileName );

    if ( file.open( QIODevice::ReadOnly ) )
    {
        m_sSeriesPoints.clear();
        m_sSeriesResults.clear();

        QTextStream in(&file);

        sHeader = in.readLine();

        while ( !in.atEnd() )
        {
            sRecord = in.readLine();

            sTokens   = sRecord.split(",");
            sFirst    = sTokens.at(0);
            sLast     = sTokens.at(1);
            sCategory = sTokens.at(2);
            sPoints   = sTokens.at(3);

            sRecord.sprintf( "%-20s, %.2d, %s %s", qPrintable( sCategory ), sPoints.toInt(), qPrintable( sFirst ), qPrintable( sLast ) );

            m_sSeriesPoints.append( sRecord );
        }

        qSort( m_sSeriesPoints );

        ui->seriesBrowser->clear();


        sHtml = "<html><body>\n";
/*
        sHtml += "<table border=1 cellspacing=0 cellpadding=10>\n";

        for ( int i = m_sSeriesPoints.count() - 1; i >= 0; i-- )
        {
            QString sBuffer;

            sTokens = m_sSeriesPoints.at(i).split(",");

            sBuffer.sprintf( "<tr><td>%s</td><td>%s</td><td>%s</td></tr>\n",
                             qPrintable( sTokens.at(0).trimmed() ),
                             qPrintable( sTokens.at(1).trimmed() ),
                             qPrintable( sTokens.at(2).trimmed() ) );

            sHtml += sBuffer;
        }

        sHtml += "</table>";
*/
        sCategory.clear();

        for ( int i = m_sSeriesPoints.count() - 1; i >= 0; i-- )
        {
            QString sBuffer;

            sTokens = m_sSeriesPoints.at(i).split(",");

            sCurrent = sTokens.at(0).trimmed();
            sPoints  = sTokens.at(1).trimmed();
            sName    = sTokens.at(2).trimmed();

            if ( sCurrent != sCategory )
            {
                if ( !sCategory.isEmpty() )
                    sHtml += "</table>\n";

                sBuffer.sprintf( "<h2>%s</h2>\n", qPrintable( sCurrent ) );
                sHtml += sBuffer;
                sHtml += "<table border=1 cellspacing=0 cellpadding=10>\n";

                sCategory = sCurrent;
            }

            sBuffer.sprintf( "<tr><td>%s</td><td>%s</td></tr>\n",
                             qPrintable( sPoints ),
                             qPrintable( sName   ) );

            sHtml += sBuffer;
        }

        sHtml += "</table>";
        sHtml += "</body></html>";

        ui->seriesBrowser->setHtml( sHtml );
        file.close();
    }
}

void MainWindow::exportSeriesResults( void )
{
    qDebug( "exportSeriesResults()" );

    QString sHtml = ui->seriesBrowser->toHtml();

    QString     sFile;

    sFile = "Spinners-tt-Series-Final-2018.html";

    QString filePath = QFileDialog::getSaveFileName(this, tr ( "Export Series Points" ),  sFile, tr ("HTML (*.html)" ));

    if ( !filePath.isEmpty() )
    {
        QFile file(filePath);

        if ( file.open( QFile::WriteOnly ) )
        {
            QTextStream stream( &file );

            stream << sHtml;

            file.close();
        }

    }

}

void MainWindow::calcSeriesResults( void )
{
    qDebug( "calcSeriesResults()" );

    QString         sRecord;

    QString         sFinish;
    QStringList     sFinishTimes;

    QString         sCategory;
    QString         sCurrent;

    QString         sName;

    QStringList     sTokens;

    QString         sPoints;
    int             cPoints;
    int             cTotal;

    QString         sHtml;

    //  Process Finish Times
    for ( int iRow = 0; iRow < ui->finishTimes->rowCount(); iRow++ )
    {
        sFinish.sprintf( "%-20s, %s, %s %s",
                         qPrintable( ui->finishTimes->item( iRow, 3 )->text() ),
                         qPrintable( ui->finishTimes->item( iRow, 5 )->text() ),
                         qPrintable( ui->finishTimes->item( iRow, 2 )->text() ),
                         qPrintable( ui->finishTimes->item( iRow, 1 )->text() ) );

        sFinishTimes.append( sFinish );
    }

    qSort( sFinishTimes );

    cPoints = 5;    //  Award Points for top 5 places

    //  Process Each Category Awarding Points
    for ( int iRow = 0; iRow < sFinishTimes.count(); iRow++ )
    {
        sTokens  = sFinishTimes.at(iRow).split(",");
        sCurrent = sTokens.at(0);

        if ( sCategory != sCurrent )    //  New Category!
        {
            cPoints = 5;
        }

        //  Save to Compare with Next Record Category
        sCategory = sCurrent;

        sPoints.sprintf( "%s,%d", qPrintable( sFinishTimes.at(iRow) ), cPoints );
        sFinishTimes.replace( iRow, sPoints );

        if ( cPoints > 0 )  cPoints--;
    }

//  ui->seriesBrowser->clear();

    //  Process Finish List Points and Update Series Points!
    for ( int iRow = 0; iRow < sFinishTimes.count(); iRow++ )
    {
        sFinish = sFinishTimes.at(iRow);
        sTokens = sFinish.split(",");

        sCategory = sTokens.at(0).trimmed();
        sName     = sTokens.at(2).trimmed();
        cPoints   = sTokens.at(3).toInt();

        //  Find Current Finisher in Series Points
        bool    bFound = false;
        for ( int i = 0; i < m_sSeriesPoints.count() && !bFound; i++ )
        {
            sFinish = m_sSeriesPoints.at(i);
            sTokens = sFinish.split(",");

            if ( sCategory == sTokens.at(0).trimmed() && sName == sTokens.at(2).trimmed() )
            {
                bFound = true;

                cTotal = sTokens.at(1).trimmed().toInt() + cPoints;

                //  Update Current Record
                sRecord.sprintf( "%-20s, %.2d, %s", qPrintable( sCategory ), cTotal, qPrintable( sName ) );

                m_sSeriesPoints.replace( i, sRecord );
            }
        }

        if ( !bFound )
        {
            //  First Time Racer!
            sRecord.sprintf( "%-20s, %.2d, %s", qPrintable( sCategory ), cPoints, qPrintable( sName ) );
            qDebug( "Not Found: %s", qPrintable( sRecord ) );

            m_sSeriesPoints.append( sRecord );
        }
    }

    sHtml = ui->seriesBrowser->toHtml();

    sHtml += "<p>\n";

    //  Today's Points!
    for ( int iRow = 0; iRow < sFinishTimes.count(); iRow++ )
    {
        sFinish.sprintf( "%s<br>\n", qPrintable( sFinishTimes.at(iRow) ) );
        sHtml += sFinish;
    }

    sHtml += "<p>\n";

    //  Output New Series Points
    qSort( m_sSeriesPoints );
/*
    sHtml += "<table border=1 cellspacing=0 cellpadding=10>\n";

    for ( int i = m_sSeriesPoints.count() - 1; i >= 0; i-- )
    {
        QString sBuffer;

        sTokens = m_sSeriesPoints.at(i).split(",");

        sBuffer.sprintf( "<tr><td>%s</td><td>%s</td><td>%s</td></tr>\n",
                         qPrintable( sTokens.at(0).trimmed() ),
                         qPrintable( sTokens.at(1).trimmed() ),
                         qPrintable( sTokens.at(2).trimmed() ) );

        sHtml += sBuffer;
    }
*/
    sCategory.clear();

    for ( int i = m_sSeriesPoints.count() - 1; i >= 0; i-- )
    {
        QString sBuffer;

        sTokens = m_sSeriesPoints.at(i).split(",");

        sCurrent = sTokens.at(0).trimmed();
        sPoints  = sTokens.at(1).trimmed();
        sName    = sTokens.at(2).trimmed();

        if ( sCurrent != sCategory )
        {
            if ( !sCategory.isEmpty() )
                sHtml += "</table>\n";

            sBuffer.sprintf( "<h2>%s</h2>\n", qPrintable( sCurrent ) );
            sHtml += sBuffer;
            sHtml += "<table border=1 cellspacing=0 cellpadding=10>\n";

            sCategory = sCurrent;
        }

        sBuffer.sprintf( "<tr><td>%s</td><td>%s</td></tr>\n",
                         qPrintable( sPoints ),
                         qPrintable( sName   ) );

        sHtml += sBuffer;
    }

    sHtml += "</table>";
    sHtml += "</body></html>";


    ui->seriesBrowser->setHtml( sHtml );

}
