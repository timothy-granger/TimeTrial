#include "StarterDialog.h"
#include "ui_StarterDialog.h"

StarterDialog::StarterDialog(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::StarterDialog)
{
    ui->setupUi(this);

    m_sOnTheLine.clear();
    m_sNextRider.clear();
    m_sCountdown.clear();
}

StarterDialog::~StarterDialog()
{
    delete ui;
}

void StarterDialog::setRaceTime( QTime time )
{
    m_raceTime = time;

    update();
}
void StarterDialog::setOnTheLine( QString sRider )
{
//  qDebug( "On The Line : %s", qPrintable( sRider ) );

    m_sOnTheLine = sRider;

    update();
}

void StarterDialog::setNextRider( QString sRider)
{
//  qDebug( "Next Rider : %s", qPrintable( sRider ) );

    m_sNextRider = sRider;

    update();
}

void StarterDialog::setRiderBib( QString sBib )
{
    m_sRiderBib = sBib;

    update();
}

void StarterDialog::updateCounter( QString sTime )
{
//  qDebug( "Counter : %s", qPrintable( sTime ) );

    m_sCountdown = sTime;

    update();
}

void StarterDialog::paintEvent( QPaintEvent *pEvent )
{
    QPainter     painter(this);

    QString      sValue;

    QFont        riderFont("Times",  75, QFont::Bold) ;
    QFont        clockFont("Times", 400, QFont::Bold) ;
    QFont        raceFont ("Times",  65, QFont::Bold) ;

    painter.setFont( riderFont );

    QFontMetrics    fmRider = painter.fontMetrics();

    int          cX = 0;
    int          cY = 0;

    //  Rider on the Line
    sValue.sprintf( "%s", qPrintable( m_sOnTheLine ) );

    cX = ( width() / 2 ) - ( fmRider.width(sValue) / 2 );
    cY = fmRider.height() * 1.1;

    painter.drawText( cX, cY, sValue );

    cY += fmRider.height() * 1.1;

    //  Rider Countdown
    painter.setFont( clockFont );

    QFontMetrics fmClock = painter.fontMetrics();

    sValue.sprintf( "%s", qPrintable( m_sCountdown ) );

    cX = ( width() / 2 ) - ( fmClock.width(sValue) / 2 );
    cY += ( fmClock.height() / 2 ) * 1.1;

    painter.drawText( cX, cY, sValue );

    //  Race Clock
    painter.setFont( raceFont );

    QFontMetrics    fmRace = painter.fontMetrics();

    sValue = QString( "%1" ).arg( m_raceTime.toString( "h:mm:ss ap" ) );

    cX = 10;
    cY = height() - 25;

    painter.drawText( cX, cY, sValue );

    //  Bib # of Rider on The Line
    sValue = QString( "%1" ).arg( m_sRiderBib );

    cX = width() - fmRace.horizontalAdvance(sValue) - 10;

    painter.drawText( cX, cY, sValue );
}
void StarterDialog::resizeEvent( QResizeEvent *event )
{
    QRect myLabel = ui->label->geometry();

    int x = ( width() * 0.6 ) - myLabel.width() / 2;
    ui->label->move( x, myLabel.y() );

}
