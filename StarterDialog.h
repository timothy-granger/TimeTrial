#ifndef STARTERDIALOG_H
#define STARTERDIALOG_H

#include <QDialog>
#include <QPainter>
#include <QTime>

namespace Ui {
class StarterDialog;
}

class StarterDialog : public QDialog
{
    Q_OBJECT

public:
    explicit StarterDialog(QWidget *parent = 0);
    ~StarterDialog();

    void        setOnTheLine( QString );
    void        setNextRider( QString );
    void        setRiderBib ( QString );

    void        setRaceTime( QTime );

    void        updateCounter( QString sTime );

protected:

    void        paintEvent( QPaintEvent * );
    void        resizeEvent( QResizeEvent * );

private:
    Ui::StarterDialog *ui;

    QTime       m_raceTime;     //  Official TT Race Clock (time of day)

    QString     m_sOnTheLine;   //  The Next Rider Starting
    QString     m_sNextRider;   //  The Next Rider to the Line
    QString     m_sRiderBib;    //  The Bib # of Next Rider Starting
    QString     m_sCountdown;   //  # of Seconds until Start
};

#endif // STARTERDIALOG_H
